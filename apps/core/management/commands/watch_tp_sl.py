"""Observateur TP/SL : clôture les positions dont le take profit ou stop loss est atteint.

Usage :
    python manage.py watch_tp_sl            # boucle infinie (intervalle TRADING_WATCHER_INTERVAL_SECONDS)
    python manage.py watch_tp_sl --once     # un seul passage (test, cron, tâche planifiée)
    python manage.py watch_tp_sl --interval 30

Pour les positions LIVE spot Kraken, la clôture envoie un ordre de vente réel au marché.
"""
import logging
import time
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.trading_service import check_tp_sl
from apps.core.watcher_health import touch_watcher_heartbeat

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Surveille les TP/SL des positions ouvertes et les clôture quand un niveau est atteint."

    def add_arguments(self, parser):
        parser.add_argument(
            '--once', action='store_true',
            help="Un seul passage puis sortie (au lieu de boucler indéfiniment).",
        )
        parser.add_argument(
            '--interval', type=int, default=settings.TRADING_WATCHER_INTERVAL_SECONDS,
            help="Intervalle entre deux passages, en secondes (défaut : %(default)s).",
        )

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(
            f"Observateur TP/SL démarré (intervalle : {interval}s). Ctrl+C pour arrêter."
        )
        while True:
<<<<<<< HEAD
            try:
                touch_watcher_heartbeat()
=======
            # Le heartbeat n'est écrit qu'APRÈS un cycle réussi : un cycle qui plante
            # doit laisser le heartbeat se périmer (signal de fraîcheur fiable pour l'alerte).
            try:
>>>>>>> dev
                for event in check_tp_sl():
                    trade = event['trade']
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ {trade.symbol} clôturé ({event['reason']}) à {event['price']} "
                        f"[{trade.trade_mode}]"
                    ))
                touch_watcher_heartbeat()
            except Exception:
<<<<<<< HEAD
                # Une panne réseau ou BDD transitoire ne doit pas tuer le worker.
                logger.exception('Erreur pendant un cycle de surveillance TP/SL')
=======
                logger.exception('Watcher cycle failed unexpectedly.')
                self.stderr.write(self.style.ERROR('✗ Cycle en échec, voir logs — heartbeat non mis à jour.'))
>>>>>>> dev
            if options['once']:
                return
            time.sleep(interval)
