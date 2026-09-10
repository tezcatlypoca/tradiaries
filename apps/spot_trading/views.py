from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.core.models import SpotTrading
from apps.core.forms import SpotTradingForm, add_form_errors_to_messages
from apps.core.portfolio_service import compute_spot_stats


@login_required
def spot_trading(request):
    trade_mode = request.GET.get('mode', 'ALL').upper()
    if trade_mode not in ('LIVE', 'PAPER'):
        trade_mode = None

    trades = SpotTrading.objects.all().order_by('-entry_date')
    if trade_mode:
        trades = trades.filter(trade_mode=trade_mode)
    stats = compute_spot_stats(trade_mode=trade_mode)
    kpi_cards = [
        {'label': "Capital engagé (positions ouvertes)", 'value': stats['capital_investi']},
        {'label': "Valeur actuelle (positions ouvertes)", 'value': stats['valeur_actuelle']},
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
        'active_mode': trade_mode or 'ALL',
    }
    return render(request, 'spot_trading/spot_trading.html', context)


@require_http_methods(["POST"])
@login_required
def create_trade(request):
    form = SpotTradingForm(request.POST)
    if form.is_valid():
        trade = form.save()
        messages.success(request, f'✓ Position {trade.symbol} créée avec succès !')
    else:
        add_form_errors_to_messages(request, form)

    return redirect('spot_trading:index')


@require_http_methods(["POST"])
@login_required
def update_trade(request, pk):
    trade = get_object_or_404(SpotTrading, pk=pk)
    form = SpotTradingForm(request.POST, instance=trade)
    if form.is_valid():
        trade = form.save()
        messages.success(request, f'✓ Position {trade.symbol} modifiée avec succès !')
    else:
        add_form_errors_to_messages(request, form)

    return redirect('spot_trading:index')


@require_http_methods(["POST"])
@login_required
def delete_trade(request, pk):
    trade = get_object_or_404(SpotTrading, pk=pk)
    symbol = trade.symbol
    trade.delete()
    messages.success(request, f'✓ Position {symbol} supprimée avec succès !')

    return redirect('spot_trading:index')
