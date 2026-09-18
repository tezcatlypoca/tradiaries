"""Agrégation des données de la BDD pour les statistiques du dashboard.

Le calcul de valeur/PnL "actuel" dépend des prix de marché en temps réel
(récupérés via l'API publique Kraken, voir kraken_client.fetch_current_prices).
L'historique du graphique, lui, ne dispose d'aucune source de prix passés :
il représente donc le capital cumulé investi (coût d'achat) au fil du temps,
et non une valorisation mark-to-market.
"""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import logging

from .kraken_client import KrakenAPIError, fetch_current_prices, fetch_trades_history, parse_symbol_from_pair
from .models import FuturesTrading, SimpleInvestment, SpotTrading

logger = logging.getLogger(__name__)


def sync_kraken_trades(user) -> dict:
    """Importe les nouveaux trades de l'historique Kraken (DCA inclus) dans SimpleInvestment.

    Idempotent : les trades déjà importés (identifiés par leur txid Kraken, stocké
    dans `external_ref`) sont ignorés.
    """
    try:
        result = fetch_trades_history(user)
    except KrakenAPIError as exc:
        logger.warning('Kraken trade synchronization failed: %s', exc)
        return {'status': 'error', 'error': str(exc), 'created': 0, 'skipped': 0}

    trades = result.get('trades', {})
    created_count = 0
    skipped_count = 0

    for txid, trade in trades.items():
        if SimpleInvestment.objects.filter(external_ref=txid).exists():
            skipped_count += 1
            continue

        SimpleInvestment.objects.create(
            user=user,
            symbol=parse_symbol_from_pair(trade.get('pair', '')),
            amount=Decimal(trade['vol']),
            price=Decimal(trade['price']),
            action='ACHAT' if trade.get('type') == 'buy' else 'VENTE',
            entry_date=datetime.fromtimestamp(float(trade['time']), tz=timezone.utc),
            notes=f"Importé depuis Kraken (txid: {txid})",
            external_ref=txid,
        )
        created_count += 1

    logger.info(
        'Kraken trade synchronization completed: created=%s skipped=%s',
        created_count,
        skipped_count,
    )
    return {'status': 'ok', 'created': created_count, 'skipped': skipped_count}



def compute_investment_stats(user) -> dict:
    """Stats Simple Invest : position nette par symbole (achats - ventes), valorisée au prix Kraken."""
    holdings = defaultdict(Decimal)
    capital_investi = Decimal('0')
    nb_positions = 0
    for inv in SimpleInvestment.objects.filter(user=user):
        nb_positions += 1
        signed_amount = inv.amount if inv.action == 'ACHAT' else -inv.amount
        holdings[inv.symbol] += signed_amount
        capital_investi += signed_amount * inv.price

    held_symbols = {symbol for symbol, qty in holdings.items() if qty > 0}
    prices, unavailable_symbols = fetch_current_prices(held_symbols)

    valeur_actuelle = sum(
        (qty * prices[symbol] for symbol, qty in holdings.items() if qty > 0 and symbol in prices),
        Decimal('0'),
    )
    pnl = valeur_actuelle - capital_investi

    return {
        'capital_investi': capital_investi,
        'valeur_actuelle': valeur_actuelle,
        'pnl': pnl,
        'nb_positions': nb_positions,
        'nb_symbols': len(held_symbols),
        'unavailable_symbols': sorted(unavailable_symbols),
    }


def compute_spot_stats(user, trade_mode: str | None = None) -> dict:
    """Stats Spot Trading : positions ouvertes (exit_price non renseigné) vs clôturées.

    Args:
        trade_mode: si renseigné ('LIVE' ou 'PAPER'), ne prend en compte que les positions de ce mode.
    """
    queryset = SpotTrading.objects.filter(user=user)
    if trade_mode:
        queryset = queryset.filter(trade_mode=trade_mode)

    open_trades = []
    closed_trades = []
    pnl_realized = Decimal('0')
    for t in queryset:
        if t.exit_price is None:
            open_trades.append(t)
        else:
            closed_trades.append(t)
            pnl_realized += (t.effective_exit_price() - t.entry_price) * t.amount

    capital_investi = sum((t.amount * t.entry_price for t in open_trades), Decimal('0'))
    prices, unavailable_symbols = fetch_current_prices({t.symbol for t in open_trades})

    valeur_actuelle = sum(
        (t.amount * prices[t.symbol] for t in open_trades if t.symbol in prices),
        Decimal('0'),
    )
    pnl_unrealized = valeur_actuelle - capital_investi
    pnl_total = pnl_unrealized + pnl_realized

    return {
        'capital_investi': capital_investi,
        'valeur_actuelle': valeur_actuelle,
        'pnl_realized': pnl_realized,
        'pnl_unrealized': pnl_unrealized,
        'pnl_total': pnl_total,
        'nb_open': len(open_trades),
        'nb_closed': len(closed_trades),
        'unavailable_symbols': sorted(unavailable_symbols),
    }


def futures_trade_pnl(trade: FuturesTrading) -> Decimal | None:
    """PnL réalisé d'une position futures clôturée (exit_price renseigné), selon la direction.

    Retourne None si la position est encore ouverte.
    """
    if trade.exit_price is None:
        return None
    exit_price = trade.effective_exit_price()
    if trade.direction == 'LONG':
        return (exit_price - trade.entry_price) * trade.amount
    return (trade.entry_price - exit_price) * trade.amount


def compute_futures_stats(user, trade_mode: str | None = None) -> dict:
    """Stats Futures Trading : idem Spot, mais le PnL dépend de la direction LONG/SHORT.

    Args:
        trade_mode: si renseigné ('LIVE' ou 'PAPER'), ne prend en compte que les positions de ce mode.
    """
    queryset = FuturesTrading.objects.filter(user=user)
    if trade_mode:
        queryset = queryset.filter(trade_mode=trade_mode)

    open_trades = []
    closed_trades = []
    pnl_realized = Decimal('0')
    for t in queryset:
        if t.exit_price is None:
            open_trades.append(t)
        else:
            closed_trades.append(t)
            pnl_realized += futures_trade_pnl(t)

    capital_investi = sum((t.amount * t.entry_price for t in open_trades), Decimal('0'))
    prices, unavailable_symbols = fetch_current_prices({t.symbol for t in open_trades})

    pnl_unrealized = Decimal('0')
    for t in open_trades:
        price = prices.get(t.symbol)
        if price is None:
            continue
        if t.direction == 'LONG':
            pnl_unrealized += (price - t.entry_price) * t.amount
        else:
            pnl_unrealized += (t.entry_price - price) * t.amount

    # Pas d'avoir "détenu" pour un future : la valeur retenue est la marge engagée + le PnL latent.
    valeur_actuelle = capital_investi + pnl_unrealized
    pnl_total = pnl_unrealized + pnl_realized

    return {
        'capital_investi': capital_investi,
        'valeur_actuelle': valeur_actuelle,
        'pnl_realized': pnl_realized,
        'pnl_unrealized': pnl_unrealized,
        'pnl_total': pnl_total,
        'nb_open': len(open_trades),
        'nb_closed': len(closed_trades),
        'unavailable_symbols': sorted(unavailable_symbols),
    }


def compute_global_stats(user) -> dict:
    """Stats agrégées toutes catégories confondues, pour le dashboard général.

    Les positions spot et futures en mode Paper sont exclues (positions fictives,
    ne doivent pas fausser le résumé du portefeuille réel).
    """
    investment = compute_investment_stats(user)
    spot = compute_spot_stats(user, trade_mode='LIVE')
    futures = compute_futures_stats(user, trade_mode='LIVE')

    portfolio_value = investment['valeur_actuelle'] + spot['valeur_actuelle'] + futures['valeur_actuelle']
    capital_investi_total = investment['capital_investi'] + spot['capital_investi'] + futures['capital_investi']
    pnl_global = investment['pnl'] + spot['pnl_total'] + futures['pnl_total']
    unavailable_symbols = sorted(
        set(investment['unavailable_symbols']) | set(spot['unavailable_symbols']) | set(futures['unavailable_symbols'])
    )

    return {
        'portfolio_value': portfolio_value,
        'capital_investi_total': capital_investi_total,
        'pnl_global': pnl_global,
        'unavailable_symbols': unavailable_symbols,
    }


def _breakdown_by(closed_trades: list, pnls: dict, key_func) -> list[dict]:
    """Ventile le PnL réalisé des trades clôturés par une clé (stratégie, symbole, ressenti...)."""
    agg = defaultdict(lambda: {'count': 0, 'pnl': Decimal('0')})
    for t in closed_trades:
        key = key_func(t)
        agg[key]['count'] += 1
        agg[key]['pnl'] += pnls[t.pk]

    rows = [{'label': key, 'count': v['count'], 'pnl': v['pnl']} for key, v in agg.items()]
    return sorted(rows, key=lambda r: r['pnl'], reverse=True)


def compute_futures_analytics(user, trade_mode: str) -> dict:
    """Statistiques de performance (win rate, R, ventilations) pour un mode donné (LIVE ou PAPER).

    Contrairement à `compute_futures_stats`, ces chiffres portent uniquement sur les positions
    clôturées (le but est d'évaluer la performance passée, pas la valeur du portefeuille).
    """
    trades = list(FuturesTrading.objects.filter(user=user, trade_mode=trade_mode).order_by('-entry_date'))
    closed = [t for t in trades if t.exit_price is not None]
    open_trades = [t for t in trades if t.exit_price is None]

    pnls = {t.pk: futures_trade_pnl(t) for t in closed}
    wins = [t for t in closed if pnls[t.pk] > 0]
    losses = [t for t in closed if pnls[t.pk] <= 0]

    gross_win = sum((pnls[t.pk] for t in wins), Decimal('0'))
    gross_loss = sum((pnls[t.pk] for t in losses), Decimal('0'))
    total_pnl = gross_win + gross_loss

    win_rate = (Decimal(len(wins)) / len(closed) * 100) if closed else None
    avg_win = (gross_win / len(wins)) if wins else Decimal('0')
    avg_loss = (gross_loss / len(losses)) if losses else Decimal('0')
    profit_factor = (gross_win / abs(gross_loss)) if gross_loss != 0 else None

    rr_values = [t.risk_reward_ratio for t in closed if t.risk_reward_ratio is not None]
    avg_rr = (sum(rr_values, Decimal('0')) / len(rr_values)) if rr_values else None

    best_trade = max(closed, key=lambda t: pnls[t.pk], default=None)
    worst_trade = min(closed, key=lambda t: pnls[t.pk], default=None)

    return {
        'trade_mode': trade_mode,
        'nb_open': len(open_trades),
        'nb_closed': len(closed),
        'nb_wins': len(wins),
        'nb_losses': len(losses),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'avg_rr': avg_rr,
        'total_pnl': total_pnl,
        'best_trade': best_trade,
        'best_trade_pnl': pnls.get(best_trade.pk) if best_trade else None,
        'worst_trade': worst_trade,
        'worst_trade_pnl': pnls.get(worst_trade.pk) if worst_trade else None,
        'by_strategy': _breakdown_by(closed, pnls, lambda t: t.strategy or 'Non renseignée'),
        'by_symbol': _breakdown_by(closed, pnls, lambda t: t.symbol),
        'by_feeling': _breakdown_by(closed, pnls, lambda t: t.get_feeling_display() if t.feeling else 'Non renseigné'),
        'by_direction': _breakdown_by(closed, pnls, lambda t: t.get_direction_display()),
    }


def _cumulative_series(events: list[tuple]) -> list[dict]:

    """Transforme une liste (date, delta) en série cumulée triée, un point par date."""
    by_date = defaultdict(Decimal)
    for date, delta in events:
        by_date[date] += delta

    series = []
    running = Decimal('0')
    for date in sorted(by_date):
        running += by_date[date]
        series.append({'time': date.isoformat(), 'value': float(running)})
    return series


def build_chart_series(user) -> dict:
    """Construit les séries 'capital cumulé investi' par catégorie pour le graphique du dashboard."""
    investment_events = [
        (inv.entry_date.date(), (inv.amount if inv.action == 'ACHAT' else -inv.amount) * inv.price)
        for inv in SimpleInvestment.objects.filter(user=user)
    ]
    # Les positions Paper sont fictives : exclues du graphique de capital investi réel.
    spot_events = [
        (t.entry_date.date(), t.amount * t.entry_price)
        for t in SpotTrading.objects.filter(user=user, trade_mode='LIVE')
    ]
    futures_events = [
        (t.entry_date.date(), t.amount * t.entry_price)
        for t in FuturesTrading.objects.filter(user=user, trade_mode='LIVE')
    ]

    return {
        'investment': _cumulative_series(investment_events),
        'spot': _cumulative_series(spot_events),
        'futures': _cumulative_series(futures_events),
        'all': _cumulative_series(investment_events + spot_events + futures_events),
    }
