"""Import du journal de trading Futures exporté depuis Notion (CSV) vers FuturesTrading."""
import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone as dj_timezone

from apps.core.models import FuturesTrading
from apps.core.parsing import normalize_decimal

_FR_MONTHS = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
    'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
}


def parse_french_date(raw: str) -> datetime | None:
    """Parse une date au format "20 août 2026" (nom de mois en français)."""
    parts = raw.strip().lower().split()
    if len(parts) != 3:
        return None
    day_str, month_name, year_str = parts
    month = _FR_MONTHS.get(month_name)
    if month is None or not day_str.isdigit() or not year_str.isdigit():
        return None
    try:
        return datetime(int(year_str), month, int(day_str))
    except ValueError:
        return None


def import_futures_journal(path: str):
    if not os.path.exists(path):
        print(f"❌ Erreur : Fichier '{path}' non trouvé.")
        return {'status': '404', 'msg': 'File not found.'}
    elif not path.endswith('.csv'):
        print(f"❌ Erreur : '{path}' n'est pas un fichier CSV.")
        return {'status': '403', 'msg': 'Is not CSV file.'}

    created = 0
    skipped_existing = 0
    skipped_invalid = 0

    try:
        with open(path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')

            for row_num, row in enumerate(reader, start=2):
                symbol = (row.get('Market') or '').strip().upper()
                direction = (row.get('Direction') or '').strip().upper()
                if not symbol or direction not in ('LONG', 'SHORT'):
                    print(f"⚠️  Ligne {row_num} ignorée : symbole ou direction manquant/invalide.")
                    skipped_invalid += 1
                    continue

                entry_price = normalize_decimal(row.get('Entry Price'))
                exit_price = normalize_decimal(row.get('Exit Price'))
                pnl = normalize_decimal(row.get('P/L'))
                if entry_price is None or exit_price is None or pnl is None:
                    print(f"⚠️  Ligne {row_num} ignorée : prix d'entrée/sortie ou P/L invalide.")
                    skipped_invalid += 1
                    continue

                # Aucune quantité n'est fournie par l'export Notion : on la déduit du P/L
                # noté, de sorte que le PnL recalculé par l'application corresponde exactement.
                price_delta = (exit_price - entry_price) if direction == 'LONG' else (entry_price - exit_price)
                if price_delta == 0:
                    print(f"⚠️  Ligne {row_num} ignorée : prix d'entrée = prix de sortie, quantité indéterminable.")
                    skipped_invalid += 1
                    continue
                amount = abs(pnl / price_delta).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

                entry_date = parse_french_date(row.get('Date', ''))
                if entry_date is None:
                    print(f"⚠️  Ligne {row_num} ignorée : date invalide ({row.get('Date')!r}).")
                    skipped_invalid += 1
                    continue

                strategy = (row.get('Strategy') or '').strip()
                risk_reward_ratio = normalize_decimal(row.get('RR'))
                exit_price_2 = normalize_decimal(row.get('2e exit'))
                feeling = (row.get('Feeling') or '').strip()
                why = (row.get('Why ?') or '').strip()
                notes = (row.get('Comments') or '').strip()

                _, was_created = FuturesTrading.objects.get_or_create(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    entry_date=dj_timezone.make_aware(entry_date),
                    strategy=strategy,
                    defaults={
                        'amount': amount,
                        'exit_price_2': exit_price_2,
                        'risk_reward_ratio': risk_reward_ratio,
                        'feeling': feeling,
                        'why': why,
                        'notes': notes,
                    },
                )
                if was_created:
                    created += 1
                    print(f"✓ {symbol} {direction} ({row.get('Date')}) - amount={amount} @ {entry_price}->{exit_price} (P/L noté: {pnl})")
                else:
                    skipped_existing += 1

            print(
                f"\n✅ {created} trade(s) importé(s), "
                f"{skipped_existing} déjà présent(s), {skipped_invalid} ligne(s) invalide(s) ignorée(s)."
            )
            return {
                'status': '200',
                'msg': f'{created} imported, {skipped_existing} duplicates, {skipped_invalid} invalid',
            }
    except Exception as e:
        print(f"❌ Erreur lors de l'import : {str(e)}")
        return {'status': '500', 'msg': str(e)}


if __name__ == '__main__':
    default_path = (
        "docs/futures_trades/Trading Journal/"
        "Free Trading Journal DB 1b9781588f9e81cca86acfb0b319ccdd.csv"
    )
    result = import_futures_journal(path=default_path)
    print(result)
