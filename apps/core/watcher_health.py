"""Heartbeat partagé (en BDD) entre le watcher TP/SL et le endpoint de supervision.

Stocké en BDD (et non sur disque) car le watcher et le serveur web peuvent
tourner sur des machines distinctes sans système de fichiers commun
(ex. worker Railway pour le watcher, web Render pour /healthz/watcher/).
"""
from django.conf import settings
from django.utils import timezone

from .models import WatcherHeartbeat


def touch_watcher_heartbeat() -> None:
    """Enregistre l'instant du dernier cycle réussi du watcher."""
    WatcherHeartbeat.objects.update_or_create(pk=1, defaults={'last_heartbeat': timezone.now()})


def watcher_is_healthy() -> bool:
    """Retourne True si le heartbeat du watcher est récent."""
    heartbeat = WatcherHeartbeat.objects.filter(pk=1).values_list('last_heartbeat', flat=True).first()
    if heartbeat is None:
        return False

    age = (timezone.now() - heartbeat).total_seconds()
    return age <= settings.TRADING_WATCHER_HEARTBEAT_TIMEOUT_SECONDS