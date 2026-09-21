import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from config.gunicorn import on_starting


class GunicornMigrationHookTests(SimpleTestCase):
    def setUp(self) -> None:
        self.server = SimpleNamespace(log=Mock())

    @patch('config.gunicorn.call_command')
    def test_migrations_are_disabled_by_default(self, call_command: Mock) -> None:
        with patch.dict(os.environ, {}, clear=True):
            on_starting(self.server)

        call_command.assert_not_called()

    @patch('config.gunicorn.call_command')
    def test_migrations_run_before_workers_when_enabled(self, call_command: Mock) -> None:
        with patch.dict(os.environ, {'RUN_MIGRATIONS_ON_START': 'true'}, clear=True):
            on_starting(self.server)

        call_command.assert_called_once_with('migrate', interactive=False)
        self.server.log.info.assert_called_once()
