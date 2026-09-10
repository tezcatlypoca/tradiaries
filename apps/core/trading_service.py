"""Orchestration des prises de position réelles (Kraken) et simulées (paper).

Règles :
- Mode PAPER : rien n'est envoyé à Kraken, la position est juste enregistrée en BDD.
- Mode LIVE spot : ordre réel via l'API Kraken classic (AddOrder).
- Mode LIVE futures : non supporté (nécessite l'API Kraken Futures, clés séparées).
- TP/SL : surveillés par l'app (commande `watch_tp_sl`), qui envoie l'ordre de
  clôture quand le niveau est atteint. Kraken classic ne gère pas ça nativement
  pour deux triggers simultanés, d'où l'observateur interne.
"""
from decimal import Decimal
import logging
import time

from .kraken_client import (
    KrakenAPIError,
    add_spot_order,
    fetch_current_price,
    fetch_current_prices,
    fetch_order_fill_price,
)
from .models import FuturesTrading, SpotTrading

logger = logging.getLogger(__name__)


class TradingError(Exception):
    """Erreur métier lors de l'ouverture ou la clôture d'une position."""


def _entry_market_price(symbol: str) -> Decimal:
    """Prix courant pour une entrée 'au marché' en mode paper."""
    price = fetch_current_price(symbol)
    if price is None:
        raise TradingError(f"Prix courant indisponible pour {symbol} : impossible d'ouvrir au marché.")
    return price


def open_position(
    *,
    category: str,
    trade_mode: str,
    symbol: str,
    amount: Decimal,
    entry_price: Decimal | None,
    direction: str = 'LONG',
    take_profit: Decimal | None = None,
    stop_loss: Decimal | None = None,
    strategy: str = '',
    feeling: str = '',
    why: str = '',
    notes: str = '',
):
    """Ouvre une position spot ou futures, en mode paper (local) ou live (ordre Kraken).

    `entry_price=None` signifie une entrée au prix du marché.
    Retourne l'objet trade créé (SpotTrading ou FuturesTrading).
    """
    symbol = symbol.strip().upper()
    external_ref = None

    if trade_mode == 'LIVE':
        if category == 'FUTURES':
            raise TradingError(
                "Les ordres futures LIVE nécessitent l'API Kraken Futures "
                "(clés séparées de Kraken classic) — non implémenté. Utilisez le mode Paper."
            )
        side = 'buy'  # spot = toujours un achat à l'ouverture
        try:
            order = add_spot_order(
                symbol, side, amount,
                ordertype='market' if entry_price is None else 'limit',
                price=entry_price,
            )
        except KrakenAPIError as exc:
            raise TradingError(f"Échec de l'ordre Kraken : {exc}") from exc
        external_ref = order['txid']
        # Prix d'exécution réel : QueryOrders juste après (market => fill quasi immédiat).
        if entry_price is None:
            time.sleep(1)
            entry_price = fetch_order_fill_price(external_ref) or _entry_market_price(symbol)
        notes = f"{notes}\n[Kraken ordre {external_ref}]".strip()
    elif entry_price is None:
        entry_price = _entry_market_price(symbol)

    common = {
        'symbol': symbol,
        'amount': amount,
        'entry_price': entry_price,
        'take_profit': take_profit,
        'stop_loss': stop_loss,
        'external_ref': external_ref,
        'trade_mode': trade_mode,
        'notes': notes,
    }
    if category == 'SPOT':
        return SpotTrading.objects.create(exchange='KRAKEN', **common)
    return FuturesTrading.objects.create(
        direction=direction, strategy=strategy, feeling=feeling, why=why, **common
    )


def _close_via_kraken(trade) -> Decimal | None:
    """Envoie l'ordre de vente spot sur Kraken et retourne le prix d'exécution (ou None)."""
    try:
        order = add_spot_order(trade.symbol, 'sell', trade.amount, ordertype='market')
    except (KrakenAPIError, TradingError) as exc:
        # Position laissée ouverte : on réessaiera au prochain cycle / à la main.
        logger.warning('Kraken close order failed for %s: %s', trade, exc)
        return None
    time.sleep(1)
    fill_price = fetch_order_fill_price(order['txid'])
    trade.notes = f"{trade.notes}\n[Clôture Kraken ordre {order['txid']}]".strip()
    return fill_price or fetch_current_price(trade.symbol)


def close_position(trade, reason: str = 'manuelle', fallback_price: Decimal | None = None) -> bool:
    """Clôture une position ouverte. Retourne True si la position a été clôturée.

    - LIVE spot Kraken : ordre de vente réel au marché.
    - Sinon (paper, spot hors Kraken) : clôture locale au prix courant.
    - LIVE futures : non supporté, la position reste ouverte (False).
    """
    if trade.exit_price is not None:
        return False

    is_futures = isinstance(trade, FuturesTrading)
    if trade.trade_mode == 'LIVE':
        if is_futures:
            logger.warning('Clôture LIVE futures non supportée (position %s) — API Kraken Futures requise.', trade.pk)
            return False
        if trade.exchange == 'KRAKEN':
            exit_price = _close_via_kraken(trade)
            if exit_price is None:
                return False
        else:
            exit_price = fetch_current_price(trade.symbol)
    else:
        exit_price = fetch_current_price(trade.symbol)

    if exit_price is None:
        exit_price = fallback_price
    if exit_price is None:
        logger.warning('Clôture impossible pour %s : aucun prix disponible.', trade)
        return False

    trade.exit_price = exit_price
    trade.notes = f"{trade.notes}\n[Clôture {reason} à {exit_price}]".strip()
    trade.save()
    logger.info('Position closed: %s reason=%s exit=%s', trade, reason, exit_price)
    return True


def _tp_sl_triggered(trade, price: Decimal) -> str | None:
    """Renvoie 'TP' ou 'SL' si le niveau est atteint au prix donné, sinon None."""
    direction = getattr(trade, 'direction', 'LONG')  # spot = toujours LONG
    if direction == 'LONG':
        if trade.take_profit is not None and price >= trade.take_profit:
            return 'TP'
        if trade.stop_loss is not None and price <= trade.stop_loss:
            return 'SL'
    else:
        if trade.take_profit is not None and price <= trade.take_profit:
            return 'TP'
        if trade.stop_loss is not None and price >= trade.stop_loss:
            return 'SL'
    return None


def check_tp_sl() -> list[dict]:
    """Surveille les positions ouvertes avec TP/SL et clôture celles déclenchées.

    Retourne la liste des clôtures effectuées ({trade, reason, price}).
    """
    watched = [
        trade
        for qs in (
            SpotTrading.objects.filter(exit_price__isnull=True),
            FuturesTrading.objects.filter(exit_price__isnull=True),
        )
        for trade in qs
        if trade.take_profit is not None or trade.stop_loss is not None
    ]
    if not watched:
        return []

    prices, unavailable = fetch_current_prices({t.symbol for t in watched})
    if unavailable:
        logger.warning('TP/SL non vérifiés (prix indisponible) pour : %s', ', '.join(sorted(unavailable)))

    closed = []
    for trade in watched:
        price = prices.get(trade.symbol)
        if price is None:
            continue
        trigger = _tp_sl_triggered(trade, price)
        if trigger is None:
            continue
        fallback = trade.take_profit if trigger == 'TP' else trade.stop_loss
        if close_position(trade, reason=trigger, fallback_price=fallback):
            closed.append({'trade': trade, 'reason': trigger, 'price': trade.exit_price})
    return closed


def live_positions() -> tuple[list[dict], set]:
    """Données de suivi en temps réel des positions ouvertes (spot + futures, tous modes).

    Retourne (positions, symboles sans prix). Chaque position : référence du trade,
    prix courant, PnL latent, et distance relative au TP/SL si définis.
    """
    open_trades = list(SpotTrading.objects.filter(exit_price__isnull=True)) + list(
        FuturesTrading.objects.filter(exit_price__isnull=True)
    )
    prices, unavailable = fetch_current_prices({t.symbol for t in open_trades})

    positions = []
    for trade in open_trades:
        is_futures = isinstance(trade, FuturesTrading)
        direction = trade.direction if is_futures else 'LONG'
        price = prices.get(trade.symbol)

        pnl = None
        if price is not None:
            if direction == 'LONG':
                pnl = (price - trade.entry_price) * trade.amount
            else:
                pnl = (trade.entry_price - price) * trade.amount

        def _distance_pct(level):
            if level is None or price is None:
                return None
            return (level - price) / price * 100

        positions.append({
            'kind': 'futures' if is_futures else 'spot',
            'pk': trade.pk,
            'symbol': trade.symbol,
            'direction': direction,
            'trade_mode': trade.trade_mode,
            'amount': trade.amount,
            'entry_price': trade.entry_price,
            'entry_date': trade.entry_date,
            'take_profit': trade.take_profit,
            'stop_loss': trade.stop_loss,
            'strategy': getattr(trade, 'strategy', ''),
            'external_ref': trade.external_ref,
            'current_price': price,
            'pnl': pnl,
            'tp_distance_pct': _distance_pct(trade.take_profit),
            'sl_distance_pct': _distance_pct(trade.stop_loss),
        })
    return positions, unavailable
