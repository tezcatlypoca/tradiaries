"""Commande d'import de l'historique des trades Kraken (DCA inclus) dans SimpleInvestment."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.core.portfolio_service import sync_kraken_trades


class Command(BaseCommand):
    help = "Importe l'historique des trades Kraken (DCA inclus) dans les investissements simples d'un utilisateur."

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', required=True,
            help="Nom d'utilisateur propriétaire des clés Kraken et des investissements importés.",
        )

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options['username'])
        except get_user_model().DoesNotExist:
            raise CommandError(f"Utilisateur introuvable : {options['username']}")

        result = sync_kraken_trades(user)
        if result['status'] == 'error':
            raise CommandError(result['error'])

        self.stdout.write(self.style.SUCCESS(
            f"{result['created']} trade(s) importé(s), {result['skipped']} déjà présent(s)."
        ))

