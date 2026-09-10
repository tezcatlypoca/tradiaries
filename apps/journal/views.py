from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.core.models import FuturesTrading
from apps.core.portfolio_service import futures_trade_pnl


@login_required
def journal(request):
    trade_mode = request.GET.get('mode', '').upper()
    strategy = request.GET.get('strategy', '')
    symbol = request.GET.get('symbol', '').upper()

    trades = FuturesTrading.objects.all().order_by('-entry_date')
    if trade_mode in ('LIVE', 'PAPER'):
        trades = trades.filter(trade_mode=trade_mode)
    if strategy:
        trades = trades.filter(strategy=strategy)
    if symbol:
        trades = trades.filter(symbol=symbol)

    strategies = sorted(
        FuturesTrading.objects.exclude(strategy='').values_list('strategy', flat=True).distinct()
    )
    symbols = sorted(FuturesTrading.objects.values_list('symbol', flat=True).distinct())

    # Le PnL n'est pas un champ du modèle : on l'attache à chaque trade pour l'affichage.
    for trade in trades:
        trade.pnl = futures_trade_pnl(trade)

    context = {
        'trades': trades,
        'strategies': strategies,
        'symbols': symbols,
        'active_mode': trade_mode,
        'active_strategy': strategy,
        'active_symbol': symbol,
    }
    return render(request, 'journal/journal.html', context)
