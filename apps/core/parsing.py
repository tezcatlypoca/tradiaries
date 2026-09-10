"""Fonctions de parsing partagées entre les scripts d'import CSV."""
import re
from decimal import Decimal, InvalidOperation

# Tout ce qui n'est pas chiffre/virgule/point/moins (devises "$US", espaces insécables
# corrompues en "�", etc.)
_NON_NUMERIC_RE = re.compile(r'[^0-9,.\-]')


def normalize_decimal(raw: str) -> Decimal | None:
    """Convertit une chaîne numérique FR/EN (avec séparateurs de milliers/devises parasites) en Decimal."""
    if not raw:
        return None
    cleaned = _NON_NUMERIC_RE.sub('', raw.strip())
    if not cleaned:
        return None
    # Le dernier séparateur rencontré (',' ou '.') est le séparateur décimal ;
    # tout séparateur précédent est un séparateur de milliers à retirer.
    sep_index = max(cleaned.rfind(','), cleaned.rfind('.'))
    if sep_index == -1:
        candidate = cleaned
    else:
        integer_part = re.sub(r'[,.]', '', cleaned[:sep_index]) or '0'
        decimal_part = cleaned[sep_index + 1:]
        candidate = f"{integer_part}.{decimal_part}" if decimal_part else integer_part
    try:
        return Decimal(candidate)
    except InvalidOperation:
        return None
