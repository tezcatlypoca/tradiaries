"""Chiffrement symétrique pour les secrets stockés en BDD (clés API des plateformes)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    encryption_key = getattr(settings, 'API_CREDENTIAL_ENCRYPTION_KEY', '')
    if encryption_key:
        return Fernet(encryption_key.encode())

    # Development-only compatibility for existing local databases.
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    """Chiffre une chaîne. Retourne '' si la valeur est vide (rien à chiffrer)."""
    if not value:
        return ''
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Déchiffre une chaîne. Retourne '' si vide ou si le déchiffrement échoue (clé changée)."""
    if not value:
        return ''
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ''
