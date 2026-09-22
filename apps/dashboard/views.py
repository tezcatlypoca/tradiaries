from django.shortcuts import render, redirect, get_object_or_404
import json
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.forms import ApiCredentialForm, add_form_errors_to_messages
from apps.core.models import ApiCredential, UserPreferences
from apps.core.portfolio_service import build_chart_series, compute_global_stats

from .forms import SignupForm, UserStrategyForm


@require_GET
@never_cache
def service_worker(_request: HttpRequest) -> HttpResponse:
    """Sert le service worker à la racine (scope "/") — nécessaire pour une PWA installable."""
    sw_path = Path(settings.BASE_DIR) / 'static' / 'js' / 'service-worker.js'
    response = HttpResponse(
        sw_path.read_text(encoding='utf-8'),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    return response


@require_GET
def manifest(request: HttpRequest) -> HttpResponse:
    return render(request, 'pwa/manifest.webmanifest', content_type='application/manifest+json')


def signup(request):
    """Inscription publique : le nouveau compte démarre sans aucune donnée existante."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f'✓ Bienvenue {user.username} ! Votre compte a été créé.')
            return redirect('dashboard:index')
    else:
        form = SignupForm()

    return render(request, 'registration/signup.html', {'form': form})


# Create your views here.
@login_required
def dashboard(request):
    stats = compute_global_stats(request.user)
    chart_series = build_chart_series(request.user)

    kpi_cards = [
        {'label': 'Portfolio Value', 'value': stats['portfolio_value']},
        {'label': 'Capital investi (total)', 'value': stats['capital_investi_total']},
        {'label': 'PnL Global', 'value': stats['pnl_global'], 'signed': True},
    ]

    context = {
        'kpi_cards': kpi_cards,
        'unavailable_symbols': stats['unavailable_symbols'],
        'chart_data': json.dumps(chart_series),
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def settings_view(request: HttpRequest) -> HttpResponse:
    credentials = ApiCredential.objects.filter(user=request.user)
    preferences = UserPreferences.objects.filter(user=request.user).first()
    context = {
        'credentials': credentials,
        'platform_requirements_json': json.dumps(ApiCredential.PLATFORM_REQUIREMENTS),
        'strategy_form': UserStrategyForm(instance=preferences),
    }
    return render(request, 'dashboard/settings.html', context)


@require_http_methods(["POST"])
@login_required
def save_strategy(request: HttpRequest) -> HttpResponse:
    preferences, _created = UserPreferences.objects.get_or_create(user=request.user)
    form = UserStrategyForm(request.POST, instance=preferences)
    if form.is_valid():
        form.save()
        messages.success(request, '✓ Stratégie enregistrée avec succès !')
    else:
        add_form_errors_to_messages(request, form)

    return redirect('settings:index')


@login_required
def coaching(request: HttpRequest) -> HttpResponse:
    return render(request, 'dashboard/coaching.html')


@require_http_methods(["POST"])
@login_required
def create_api_credential(request: HttpRequest) -> HttpResponse:
    form = ApiCredentialForm(request.POST, user=request.user)
    if form.is_valid():
        credential = ApiCredential(
            user=request.user,
            platform=form.cleaned_data['platform'],
            label=form.cleaned_data['label'],
        )
        credential.set_credentials(
            api_key=form.cleaned_data['api_key'],
            api_secret=form.cleaned_data['api_secret'],
            passphrase=form.cleaned_data['passphrase'],
        )
        credential.save()
        credential.log_access('CREATE')
        messages.success(request, f'✓ Clé API {credential.get_platform_display()} enregistrée avec succès !')
    else:
        add_form_errors_to_messages(request, form)

    return redirect('settings:index')


@require_http_methods(["POST"])
@login_required
def delete_api_credential(request: HttpRequest, pk: int) -> HttpResponse:
    credential = get_object_or_404(ApiCredential, pk=pk, user=request.user)
    platform_label = credential.get_platform_display()
    credential.log_access('DELETE')
    credential.delete()
    messages.success(request, f'✓ Clé API {platform_label} supprimée avec succès !')

    return redirect('settings:index')
