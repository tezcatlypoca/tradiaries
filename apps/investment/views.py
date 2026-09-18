from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.core.models import SimpleInvestment
from apps.core.forms import SimpleInvestmentForm, add_form_errors_to_messages
from apps.core.portfolio_service import compute_investment_stats
from apps.core.watcher_health import watcher_is_healthy


def healthz(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})

def watcher_healthz(request):
    """Healthcheck du processus qui surveille les take profits et stop losses."""
    if not watcher_is_healthy():
        return JsonResponse({'status': 'error', 'watcher': 'stale'}, status=503)
    return JsonResponse({'status': 'ok', 'watcher': 'running'})


@login_required
def investment(request):
    investments = SimpleInvestment.objects.all().order_by('-entry_date')
    stats = compute_investment_stats()
    kpi_cards = [
        {'label': 'Capital investi', 'value': stats['capital_investi']},
        {'label': 'Valeur actuelle', 'value': stats['valeur_actuelle']},
        {'label': 'PnL', 'value': stats['pnl'], 'signed': True},
        {'label': 'Positions', 'value': stats['nb_positions'], 'is_count': True},
        {'label': 'Symboles détenus', 'value': stats['nb_symbols'], 'is_count': True},
    ]

    context = {
        'investments': investments,
        'kpi_cards': kpi_cards,
        'unavailable_symbols': stats['unavailable_symbols'],
    }
    return render(request, 'investment/investment.html', context)


@require_http_methods(["POST"])
@login_required
def create_investment(request):
    form = SimpleInvestmentForm(request.POST)
    if form.is_valid():
        investment = form.save()
        messages.success(request, f'✓ Investissement {investment.symbol} créé avec succès !')
    else:
        add_form_errors_to_messages(request, form)
    
    return redirect('investment:index')


@require_http_methods(["POST"])
@login_required
def update_investment(request, pk):
    investment = get_object_or_404(SimpleInvestment, pk=pk)
    form = SimpleInvestmentForm(request.POST, instance=investment)
    if form.is_valid():
        investment = form.save()
        messages.success(request, f'✓ Investissement {investment.symbol} modifié avec succès !')
    else:
        add_form_errors_to_messages(request, form)

    return redirect('investment:index')


@require_http_methods(["POST"])
@login_required
def delete_investment(request, pk):
    investment = get_object_or_404(SimpleInvestment, pk=pk)
    symbol = investment.symbol
    investment.delete()
    messages.success(request, f'✓ Investissement {symbol} supprimé avec succès !')

    return redirect('investment:index')
