from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.core.portfolio_service import compute_futures_analytics


@login_required
def analytics(request):
    trade_mode = request.GET.get('mode', 'LIVE').upper()
    if trade_mode not in ('LIVE', 'PAPER'):
        trade_mode = 'LIVE'

    stats = compute_futures_analytics(trade_mode)

    kpi_cards = [
        {'label': 'Positions clôturées', 'value': stats['nb_closed'], 'is_count': True},
        {'label': 'Positions ouvertes', 'value': stats['nb_open'], 'is_count': True},
        {'label': 'Win rate', 'value': stats['win_rate'], 'is_percent': True},
        {'label': 'Profit factor', 'value': stats['profit_factor'], 'is_ratio': True},
        {'label': 'R moyen', 'value': stats['avg_rr'], 'is_ratio': True},
        {'label': 'PnL total réalisé', 'value': stats['total_pnl'], 'signed': True},
        {'label': 'Gain moyen', 'value': stats['avg_win'], 'signed': True},
        {'label': 'Perte moyenne', 'value': stats['avg_loss'], 'signed': True},
    ]

    context = {
        'active_mode': trade_mode,
        'stats': stats,
        'kpi_cards': kpi_cards,
    }
    return render(request, 'analytics/analytics.html', context)
