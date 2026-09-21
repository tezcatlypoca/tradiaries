import os

from django.core.management import call_command


def _enabled(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def on_starting(server) -> None:
    if not _enabled(os.getenv('RUN_MIGRATIONS_ON_START', 'false')):
        return

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    server.log.info('Applying pending Django migrations before starting workers')
    call_command('migrate', interactive=False)
