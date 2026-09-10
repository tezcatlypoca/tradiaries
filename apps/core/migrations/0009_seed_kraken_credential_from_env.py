"""Migration de données : reprend les clés Kraken de .env (settings) vers ApiCredential.

Kraken devient géré exclusivement via la BDD (page Paramètres) après cette migration ;
le fichier .env garde les valeurs en backup mais n'est plus lu par kraken_client.py.
"""
from django.conf import settings
from django.db import migrations

from apps.core.crypto import encrypt


def seed_kraken_credential_from_env(apps, schema_editor):
    ApiCredential = apps.get_model('core', 'ApiCredential')
    if ApiCredential.objects.filter(platform='KRAKEN').exists():
        return

    api_key = getattr(settings, 'KRAKEN_API_KEY', '')
    api_secret = getattr(settings, 'KRAKEN_API_PRIVATE', '')
    if not api_key or not api_secret:
        return

    ApiCredential.objects.create(
        platform='KRAKEN',
        label='Migré depuis .env',
        api_key=encrypt(api_key),
        api_secret=encrypt(api_secret),
        passphrase='',
    )


def noop_reverse(apps, schema_editor):
    """Rien à défaire : on ne supprime pas une clé qui a pu être modifiée depuis."""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_apicredential'),
    ]

    operations = [
        migrations.RunPython(seed_kraken_credential_from_env, noop_reverse),
    ]
