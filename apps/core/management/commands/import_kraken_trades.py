"""Commande d'import de l'historique des trades Kraken (DCA inclus) dans SimpleInvestment."""
from django.core.management.base import BaseCommand, CommandError

from apps.core.portfolio_service import sync_kraken_trades


class Command(BaseCommand):
    help = "Importe l'historique des trades Kraken (DCA inclus) dans les investissements simples."

    def handle(self, *args, **options):
        result = sync_kraken_trades()
        if result['status'] == 'error':
            raise CommandError(result['error'])

        self.stdout.write(self.style.SUCCESS(
            f"{result['created']} trade(s) importé(s), {result['skipped']} déjà présent(s)."
        ))

