"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pathlib import Path
from apps.investment.views import healthz
from apps.investment.views import healthz, watcher_healthz
from apps.dashboard.views import service_worker, manifest

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('healthz/watcher/', watcher_healthz, name='watcher_healthz'),
    path('service-worker.js', service_worker, name='service_worker'),
    path('manifest.webmanifest', manifest, name='manifest'),
    path('', include("apps.dashboard.urls")),
    path('investment/', include("apps.investment.urls")),
    path('spot-trading/', include("apps.spot_trading.urls")),
    path('futures-trading/', include("apps.futures_trading.urls")),
    path('analytics/', include("apps.analytics.urls")),
    path('journal/', include("apps.journal.urls")),
    path('live/', include("apps.live_trading.urls")),
    path('accounts/', include('django.contrib.auth.urls')),
    path('settings/', include('apps.dashboard.settings_urls')),
    path('admin/', admin.site.urls),
]

# Servir les fichiers statiques en développement
if settings.DEBUG:
    BASE_DIR = Path(__file__).resolve().parent.parent
    urlpatterns += static(settings.STATIC_URL, document_root=BASE_DIR / 'static')
