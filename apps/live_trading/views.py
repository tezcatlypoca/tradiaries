"""Vues de la page Trading : interface exchange-like (graphique + ticket d'ordre) et suivi temps réel."""
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.kraken_client import KrakenAPIError, fetch_ohlc
from apps.core.models import FuturesTrading, SpotTrading, UserPreferences
from apps.core.trading_service import (
    TradingError,
    close_position as service_close_position,
    live_positions,
)
from apps.core.trading_service import open_position as service_open_position
from apps.core.vigil_client import fetch_signals as fetch_vigil_signals

from .forms import OpenPositionForm

# Symboles proposés par défaut dans le sélecteur d'actif (liste courte, l'utilisateur
# peut saisir n'importe quel autre symbole coté sur Kraken via le champ texte).
DEFAULT_TRADING_SYMBOLS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'DOT', 'LTC']
VALID_OHLC_INTERVALS = (15, 60, 240, 1440)


def _serialize_decimal(value):
    return None if value is None else str(value)


def _position_to_json(position: dict) -> dict:
    return {
        key: _serialize_decimal(value) if isinstance(value, Decimal) else value
        for key, value in position.items()
    } | {'entry_date': position['entry_date'].strftime('%d/%m/%Y %H:%M')}


@login_required
def live_trading(request):
    """Page Trading : ticket d'ordre + graphique par actif, positions ouvertes en temps réel."""
    positions, unavailable_symbols = live_positions(request.user)
    context = {
        'positions': positions,
        'unavailable_symbols': sorted(unavailable_symbols),
        'watcher_interval': _watcher_interval(),
        'default_symbols': DEFAULT_TRADING_SYMBOLS,
    }
    return render(request, 'live_trading/live_trading.html', context)


def _watcher_interval() -> int:
    from django.conf import settings
    return settings.TRADING_WATCHER_INTERVAL_SECONDS


@login_required
def ohlc_json(request):
    """Chandeliers OHLC (Kraken, endpoint public) pour le graphique de la page Trading."""
    symbol = request.GET.get('symbol', 'BTC').strip().upper()
    try:
        interval = int(request.GET.get('interval', 60))
    except ValueError:
        interval = 60
    if interval not in VALID_OHLC_INTERVALS:
        interval = 60

    try:
        candles = fetch_ohlc(symbol, interval=interval)
    except KrakenAPIError as exc:
        return JsonResponse({'candles': [], 'error': str(exc)})
    return JsonResponse({'candles': candles})


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
def vigil_signals_json(request):
    """Signaux Vigil filtrés : actifs suivis par l'utilisateur + signaux macro/géopolitiques (ticker=null).

    Un seul appel à Vigil par chargement de page (jamais un appel par actif suivi),
    filtrage effectué ici pour ménager le rate limit Vigil partagé entre tous les
    utilisateurs Tradiaries. Affichage neutre : pas de couleur directionnelle, pas de
    CTA d'action, `reliability_tier` conservé pour distinguer fait et opinion.
    `raw_payload` n'est jamais exposé (peut contenir des identifiants d'article/données
    brutes de la source). `impact_score`/`news_score` sont exposés depuis le 2026-09-27
    (vue détaillée de la news, décision révisée — voir `.ai/decisions.md`) : ce sont des
    scores de fiabilité/nouveauté, pas des signaux directionnels bull/bear.
    """
    preferences = UserPreferences.objects.filter(user=request.user).first()
    tracked_assets = set(preferences.tracked_assets) if preferences else set()

    signals = [
        {
            'source': signal.get('source'),
            'ticker': signal.get('ticker'),
            'summary': signal.get('summary'),
            'timestamp': signal.get('timestamp'),
            'reliability_tier': signal.get('reliability_tier'),
            'impact_score': signal.get('impact_score'),
            'news_score': signal.get('news_score'),
        }
        for signal in fetch_vigil_signals()
        if signal.get('ticker') is None or signal.get('ticker') in tracked_assets
    ]
    return JsonResponse({'signals': signals})


@login_required
def positions_json(request):
    """Endpoint de polling pour le rafraîchissement automatique du suivi live."""
    positions, unavailable_symbols = live_positions(request.user)
    return JsonResponse({
        'positions': [_position_to_json(p) for p in positions],
        'unavailable_symbols': sorted(unavailable_symbols),
    })
