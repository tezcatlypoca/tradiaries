"""Orchestration des prises de position réelles (Kraken) et simulées (paper).

Règles :
- Mode PAPER : rien n'est envoyé à Kraken, la position est juste enregistrée en BDD.
- Mode LIVE spot : ordre réel via l'API Kraken classic (AddOrder).
- Mode LIVE futures : non supporté (nécessite l'API Kraken Futures, clés séparées).
- TP/SL : surveillés par l'app (commande `watch_tp_sl`), qui envoie l'ordre de
  clôture quand le niveau est atteint. Kraken classic ne gère pas ça nativement
  pour deux triggers simultanés, d'où l'observateur interne.
- Ordre LIVE : un `KrakenOrderAttempt` est persisté AVANT tout appel réseau, avec
  un identifiant client unique. Si le processus plante entre l'acceptation Kraken
  et l'écriture de la position locale, cette trace survit pour réconciliation
  manuelle (admin) au lieu de laisser un ordre réel sans contrepartie en BDD.
"""
from decimal import Decimal
import logging
import time
import uuid

from .kraken_client import (
    KrakenAPIError,
    add_spot_order,
    fetch_current_price,
    fetch_current_prices,
    fetch_order_fill_price,
)
from .models import FuturesTrading, KrakenOrderAttempt, SpotTrading

logger = logging.getLogger(__name__)


class TradingError(Exception):
    """Erreur métier lors de l'ouverture ou la clôture d'une position."""


def _entry_market_price(symbol: str) -> Decimal:
    """Prix courant pour une entrée 'au marché' en mode paper."""
    price = fetch_current_price(symbol)
    if price is None:
        raise TradingError(f"Prix courant indisponible pour {symbol} : impossible d'ouvrir au marché.")
    return price


def _userref_from_client_order_id(client_order_id: str) -> int:
    """Dérive un userref Kraken (entier 32 bits) déterministe depuis un client_order_id."""
    return int(client_order_id[:8], 16) % 2_147_483_647


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
    attempt = None

    if trade_mode == 'LIVE':
        if category == 'FUTURES':
            raise TradingError(
                "Les ordres futures LIVE nécessitent l'API Kraken Futures "
                "(clés séparées de Kraken classic) — non implémenté. Utilisez le mode Paper."
            )
        side = 'buy'  # spot = toujours un achat à l'ouverture
        # Persisté AVANT l'appel Kraken : trace de réconciliation en cas de plantage.
        attempt = KrakenOrderAttempt.objects.create(
            client_order_id=uuid.uuid4().hex,
            operation='OPEN',
            symbol=symbol,
            side=side,
            volume=amount,
            status='PENDING',
        )
        userref = _userref_from_client_order_id(attempt.client_order_id)
        attempt.kraken_userref = userref
        try:
            order = add_spot_order(
                symbol, side, amount,
                ordertype='market' if entry_price is None else 'limit',
                price=entry_price,
                userref=userref,
            )
        except KrakenAPIError as exc:
            attempt.status = 'FAILED'
            attempt.error_message = str(exc)
            attempt.save(update_fields=['kraken_userref', 'status', 'error_message', 'updated_at'])
            raise TradingError(f"Échec de l'ordre Kraken : {exc}") from exc

        external_ref = order['txid']
        attempt.status = 'SUBMITTED'
        attempt.external_ref = external_ref
        attempt.save(update_fields=['kraken_userref', 'status', 'external_ref', 'updated_at'])

        # Prix d'exécution réel : QueryOrders juste après (market => fill quasi immédiat).
        if entry_price is None:
            time.sleep(1)
            try:
                entry_price = fetch_order_fill_price(external_ref) or _entry_market_price(symbol)
            except (KrakenAPIError, TradingError) as exc:
                # L'ordre est bien parti sur Kraken : ne PAS le faire disparaître, marquer à réconcilier.
                attempt.status = 'RECONCILE_REQUIRED'
                attempt.error_message = f"Ordre soumis (txid={external_ref}) mais fill introuvable : {exc}"
                attempt.save(update_fields=['status', 'error_message', 'updated_at'])
                raise TradingError(
                    f"Ordre envoyé à Kraken (txid {external_ref}) mais confirmation impossible : "
                    "vérifiez manuellement sur Kraken puis réconciliez (voir admin > Tentatives ordres Kraken)."
                ) from exc
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
    try:
        if category == 'SPOT':
            trade = SpotTrading.objects.create(exchange='KRAKEN', **common)
        else:
            trade = FuturesTrading.objects.create(
                direction=direction, strategy=strategy, feeling=feeling, why=why, **common
            )
    except Exception:
        if attempt is not None:
            # Ordre confirmé côté Kraken mais échec de la persistance locale : ne pas masquer l'incident.
            attempt.status = 'RECONCILE_REQUIRED'
            attempt.error_message = f"Ordre confirmé (txid={external_ref}) mais échec de création de la position locale."
            attempt.save(update_fields=['status', 'error_message', 'updated_at'])
            logger.critical(
                'Kraken order %s confirmed but local trade creation failed — manual reconciliation required.',
                external_ref,
            )
        raise

    if attempt is not None:
        attempt.status = 'CONFIRMED'
        attempt.spot_trade = trade
        attempt.save(update_fields=['status', 'spot_trade', 'updated_at'])
    return trade


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

    La position est revendiquée atomiquement (`is_closing`) avant tout appel Kraken :
    si deux appels concurrents (watcher + clic manuel, ou deux watchers) visent la
    même position, un seul obtient la revendication et envoie l'ordre de vente.
    """
    if trade.exit_price is not None:
        return False

    model = type(trade)
    claimed = model.objects.filter(pk=trade.pk, exit_price__isnull=True, is_closing=False).update(is_closing=True)
    if not claimed:
        logger.info('Close skipped for %s: already closing or closed by another process.', trade.pk)
        return False

    try:
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
        trade.is_closing = False
        trade.notes = f"{trade.notes}\n[Clôture {reason} à {exit_price}]".strip()
        trade.save()
        logger.info('Position closed: %s reason=%s exit=%s', trade, reason, exit_price)
        return True
    finally:
        # Clôture non aboutie (Kraken KO, prix indisponible...) : on relâche le verrou pour un prochain essai.
        if trade.exit_price is None:
            model.objects.filter(pk=trade.pk).update(is_closing=False)


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
        try:
            if close_position(trade, reason=trigger, fallback_price=fallback):
                closed.append({'trade': trade, 'reason': trigger, 'price': trade.exit_price})
        except Exception:
            # Isole les positions : une erreur inattendue sur l'une ne doit pas arrêter le cycle entier.
            logger.exception('Unexpected error while closing position %s (trigger=%s)', trade.pk, trigger)
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
