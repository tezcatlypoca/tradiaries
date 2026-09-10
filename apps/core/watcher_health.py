"""Heartbeat partagé entre le watcher TP/SL et le endpoint de supervision."""
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings


def touch_watcher_heartbeat() -> None:
    """Enregistre atomiquement l'instant du dernier cycle du watcher."""
    heartbeat_path = Path(settings.TRADING_WATCHER_HEARTBEAT_FILE)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = heartbeat_path.with_suffix('.tmp')
    temporary_path.write_text(
        datetime.now(timezone.utc).isoformat(),
        encoding='ascii',
    )
    temporary_path.replace(heartbeat_path)


def watcher_is_healthy() -> bool:
    """Retourne True si le heartbeat du watcher est récent."""
    heartbeat_path = Path(settings.TRADING_WATCHER_HEARTBEAT_FILE)
    try:
        heartbeat = datetime.fromisoformat(
            heartbeat_path.read_text(encoding='ascii').strip()
        )
    except (FileNotFoundError, ValueError, OSError):
        return False

    age = (datetime.now(timezone.utc) - heartbeat).total_seconds()
    return age <= settings.TRADING_WATCHER_HEARTBEAT_TIMEOUT_SECONDS