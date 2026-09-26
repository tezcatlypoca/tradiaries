"""Client minimal pour l'API Vigil (signaux de marché scorés, lecture seule).

Documentation : docs/API_DOCUMENTATION.md
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def fetch_signals() -> list[dict]:
    """Récupère les signaux persistés par Vigil (fenêtre par défaut côté Vigil : 24h).

    Ne lève jamais d'exception : Vigil est une donnée d'agrément (bandeau de contexte
    sur la page Trading), pas un prérequis de fonctionnement de l'app. Retourne une
    liste vide si l'URL n'est pas configurée, si Vigil est indisponible, ou en cas
    d'erreur réseau/format — jamais de 500 sur la page Trading à cause de Vigil.
    """
    if not settings.VIGIL_API_URL:
        return []

    headers = {}
    if settings.VIGIL_BEARER_TOKEN:
        headers['Authorization'] = f"Bearer {settings.VIGIL_BEARER_TOKEN}"

    try:
        response = requests.get(
            f"{settings.VIGIL_API_URL}/signals",
            headers=headers,
            timeout=settings.VIGIL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('Vigil signals request failed: %s', exc)
        return []

    try:
        data = response.json()
    except ValueError:
        logger.warning('Vigil returned invalid JSON on /signals')
        return []

    return data.get('signals', [])
