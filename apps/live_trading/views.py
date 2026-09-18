"""Vues de la page Trading Live : ouverture de positions (paper/live) et suivi temps réel."""
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.models import FuturesTrading, SpotTrading
from apps.core.trading_service import (
    TradingError,
    close_position as service_close_position,
    live_positions,
)
from apps.core.trading_service import open_position as service_open_position

from .forms import OpenPositionForm


def _serialize_decimal(value):
    return None if value is None else str(value)


def _position_to_json(position: dict) -> dict:
    return {
        key: _serialize_decimal(value) if isinstance(value, Decimal) else value
        for key, value in position.items()
    } | {'entry_date': position['entry_date'].strftime('%d/%m/%Y %H:%M')}


@login_required
def live_trading(request):
    """Page Trading Live : positions ouvertes avec prix et PnL en temps réel."""
    positions, unavailable_symbols = live_positions(request.user)
    context = {
        'positions': positions,
        'unavailable_symbols': sorted(unavailable_symbols),
        'watcher_interval': _watcher_interval(),
    }
    return render(request, 'live_trading/live_trading.html', context)


def _watcher_interval() -> int:
    from django.conf import settings
    return settings.TRADING_WATCHER_INTERVAL_SECONDS


@require_http_methods(["POST"])
@login_required
def open_position(request):
    form = OpenPositionForm(request.POST)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect('live_trading:index')

    data = form.cleaned_data
    for field_name in ('regime_confirmed', 'sar_confirmed', 'volume_profile_confirmed'):
        data.pop(field_name, None)
    try:
        trade = service_open_position(user=request.user, **data)
    except TradingError as exc:
        messages.error(request, f"✗ {exc}")
        return redirect('live_trading:index')

    mode = trade.get_trade_mode_display()
    if trade.trade_mode == 'LIVE':
        messages.success(request, f'✓ Ordre LIVE exécuté sur Kraken : {trade.symbol} @ {trade.entry_price}')
    else:
        messages.success(request, f'✓ Position {mode} {trade.symbol} ouverte à {trade.entry_price}')
    return redirect('live_trading:index')


@require_http_methods(["POST"])
@login_required
def close_position(request, kind, pk):
    model = FuturesTrading if kind == 'futures' else SpotTrading
    trade = get_object_or_404(model, pk=pk, user=request.user)
    if service_close_position(trade, reason='manuelle'):
        messages.success(request, f'✓ Position {trade.symbol} clôturée à {trade.exit_price}')
    else:
        messages.error(request, f"✗ Clôture impossible pour {trade.symbol} (voir logs).")
    return redirect('live_trading:index')


@login_required
def positions_json(request):
    """Endpoint de polling pour le rafraîchissement automatique du suivi live."""
    positions, unavailable_symbols = live_positions(request.user)
    return JsonResponse({
        'positions': [_position_to_json(p) for p in positions],
        'unavailable_symbols': sorted(unavailable_symbols),
    })
