import os
import csv
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone as dj_timezone

from apps.core.models import SimpleInvestment
from apps.core.parsing import normalize_decimal


def import_csv(path: str):
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
            reader = csv.reader(csvfile, delimiter=',')
            next(reader, None)  # en-tête : Nom,Acronyme,Quantite,Achat (en USDT),Vente (en USDT),Prix (en USDT),Date

            for row_num, row in enumerate(reader, start=2):
                if not any(row):
                    continue
                if len(row) < 7:
                    print(f"⚠️  Ligne {row_num} ignorée : colonnes manquantes.")
                    skipped_invalid += 1
                    continue

                name, acronym, qty_raw, buy_raw, sell_raw, price_raw, date_raw = row[:7]

                symbol = acronym.strip().upper()
                if not symbol:
                    print(f"⚠️  Ligne {row_num} ignorée : symbole manquant.")
                    skipped_invalid += 1
                    continue

                if buy_raw.strip() and not sell_raw.strip():
                    action = 'ACHAT'
                elif sell_raw.strip() and not buy_raw.strip():
                    action = 'VENTE'
                else:
                    print(f"⚠️  Ligne {row_num} ignorée : colonnes Achat/Vente ambiguës.")
                    skipped_invalid += 1
                    continue

                amount = normalize_decimal(qty_raw)
                price = normalize_decimal(price_raw)
                if amount is None or price is None:
                    print(f"⚠️  Ligne {row_num} ignorée : quantité ou prix invalide ({qty_raw!r}, {price_raw!r}).")
                    skipped_invalid += 1
                    continue

                date_str = date_raw.strip()
                try:
                    naive_date = datetime.strptime(date_str, '%d/%m/%y')
                except ValueError:
                    print(f"⚠️  Ligne {row_num} ignorée : date invalide ({date_str!r}).")
                    skipped_invalid += 1
                    continue
                entry_date = dj_timezone.make_aware(naive_date)

                _, was_created = SimpleInvestment.objects.get_or_create(
                    symbol=symbol,
                    amount=amount,
                    price=price,
                    action=action,
                    entry_date=entry_date,
                    defaults={'notes': name.strip()},
                )
                if was_created:
                    created += 1
                    print(f"✓ {symbol} ({date_str}) - {action} {amount} @ {price}")
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
    result = import_csv(path="docs/Crypto.csv")
    print(result)
