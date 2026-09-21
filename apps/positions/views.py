"""Vue de la page Positions : consultation unifiée des positions Spot et Futures.

Page de suivi uniquement (lecture) : aucune ouverture ni clôture de position ici.
L'ouverture se fait désormais depuis la page Trading (apps.live_trading), la
clôture depuis cette même page Trading ou le watcher TP/SL automatique.
Un panneau de détail (JS, voir template) remplace les anciens formulaires
d'édition en modale : la suppression reste possible (correction de saisie),
via les endpoints existants `spot_trading:delete` / `futures_trading:delete`.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.models import FuturesTrading, SpotTrading
from apps.core.portfolio_service import compute_futures_stats, compute_spot_stats

_VALID_MODES = ('LIVE', 'PAPER')
_VALID_CATEGORIES = ('SPOT', 'FUTURES')


@login_required
def positions(request):
    category = request.GET.get('category', 'SPOT').upper()
    if category not in _VALID_CATEGORIES:
        category = 'SPOT'

    trade_mode = request.GET.get('mode', 'ALL').upper()
    if trade_mode not in _VALID_MODES:
        trade_mode = None

    if category == 'SPOT':
        trades = SpotTrading.objects.filter(user=request.user, exit_price__isnull=False).order_by('-entry_date')
        stats = compute_spot_stats(request.user, trade_mode=trade_mode)
        delete_url_name = 'spot_trading:delete'
    else:
        trades = FuturesTrading.objects.filter(user=request.user, exit_price__isnull=False).order_by('-entry_date')
        stats = compute_futures_stats(request.user, trade_mode=trade_mode)
        delete_url_name = 'futures_trading:delete'

    if trade_mode:
        trades = trades.filter(trade_mode=trade_mode)

    kpi_label_capital = 'Marge engagée (positions ouvertes)' if category == 'FUTURES' else 'Capital engagé (positions ouvertes)'
    kpi_cards = [
        {'label': kpi_label_capital, 'value': stats['capital_investi']},
        {'label': 'Valeur actuelle (positions ouvertes)', 'value': stats['valeur_actuelle']},
        {'label': 'PnL réalisé', 'value': stats['pnl_realized'], 'signed': True},
        {'label': 'PnL latent', 'value': stats['pnl_unrealized'], 'signed': True},
        {'label': 'PnL total', 'value': stats['pnl_total'], 'signed': True},
        {'label': 'Positions ouvertes', 'value': stats['nb_open'], 'is_count': True},
        {'label': 'Positions clôturées', 'value': stats['nb_closed'], 'is_count': True},
    ]

    context = {
        'trades': trades,
        'kpi_cards': kpi_cards,
        'unavailable_symbols': stats['unavailable_symbols'],
        'active_category': category,
        'active_mode': trade_mode or 'ALL',
        'delete_url_name': delete_url_name,
    }
    return render(request, 'positions/positions.html', context)
