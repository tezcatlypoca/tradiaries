"""Client minimal pour l'API privée de Kraken (lecture + trading spot).

Documentation : https://docs.kraken.com/rest/#tag/Account-Data
               https://docs.kraken.com/rest/#tag/Trading
"""
import base64
import hashlib
import hmac
import time
import urllib.parse
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://api.kraken.com"
logger = logging.getLogger(__name__)


def _http_session() -> requests.Session:
    retry = Retry(
        total=settings.KRAKEN_MAX_RETRIES,
        connect=settings.KRAKEN_MAX_RETRIES,
        read=settings.KRAKEN_MAX_RETRIES,
        status=settings.KRAKEN_MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({'GET', 'POST'}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session

# Suffixes de devise de cotation les plus courants sur Kraken, dans l'ordre de test
_QUOTE_SUFFIXES = ['ZEUR', 'ZUSD', 'EUR', 'USD', 'USDT']

# Kraken utilise des codes d'actif hérités pour certains symboles
_ALT_ASSET_NAMES = {'BTC': 'XBT', 'DOGE': 'XDG'}
_PUBLIC_QUOTE_CANDIDATES = ['USD', 'USDT']
_PRICE_CACHE_TTL = 60  # secondes


class KrakenAPIError(Exception):
    """Erreur renvoyée par l'API Kraken ou lors de l'appel réseau."""


def _sign(path: str, payload: dict, secret: str) -> str:
    postdata = urllib.parse.urlencode(payload)
    encoded = (str(payload['nonce']) + postdata).encode()
    message = path.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()


def _get_kraken_credentials() -> tuple[str, str]:
    """Récupère la clé/secret Kraken depuis la BDD (ApiCredential), seule source désormais (plus de fallback .env)."""
    from .models import ApiCredential  # import différé pour éviter tout risque de cycle au chargement des apps

    credential = ApiCredential.objects.filter(platform='KRAKEN').first()
    if not credential:
        return '', ''
    return credential.get_api_key(), credential.get_api_secret()


def _private_request(endpoint: str, data: dict | None = None) -> dict:
    api_key, api_secret = _get_kraken_credentials()
    if not api_key or not api_secret:
        raise KrakenAPIError(
            "Clés API Kraken non configurées. Ajoutez-les depuis la page Paramètres."
        )

    path = f"/0/private/{endpoint}"
    payload = {'nonce': str(int(time.time() * 1000))}
    if data:
        payload.update(data)

    headers = {
        'API-Key': api_key,
        'API-Sign': _sign(path, payload, api_secret),
    }

    try:
        response = _http_session().post(
            API_URL + path,
            headers=headers,
            data=payload,
            timeout=settings.KRAKEN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('Kraken private request failed: endpoint=%s error=%s', endpoint, exc)
        raise KrakenAPIError(f"Erreur réseau lors de l'appel à Kraken : {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        logger.warning('Kraken returned invalid JSON: endpoint=%s', endpoint)
        raise KrakenAPIError("Réponse invalide reçue de Kraken.") from exc
    if result.get('error'):
        raise KrakenAPIError(', '.join(result['error']))
    return result['result']


def fetch_trades_history() -> dict:
    """Récupère l'historique des trades exécutés sur le compte Kraken."""
    return _private_request('TradesHistory')


def _public_request(endpoint: str, params: dict | None = None) -> dict:
    try:
        response = _http_session().get(
            f"{API_URL}/0/public/{endpoint}",
            params=params or {},
            timeout=settings.KRAKEN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('Kraken public request failed: endpoint=%s error=%s', endpoint, exc)
        raise KrakenAPIError(f"Erreur réseau lors de l'appel à Kraken : {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        logger.warning('Kraken returned invalid JSON: endpoint=%s', endpoint)
        raise KrakenAPIError("Réponse invalide reçue de Kraken.") from exc
    if result.get('error'):
        raise KrakenAPIError(', '.join(result['error']))
    return result['result']


def fetch_current_price(symbol: str) -> Decimal | None:
    """Récupère le dernier prix coté (endpoint public Ticker) d'un symbole, ou None si absent de Kraken.

    Le résultat est mis en cache 60s pour éviter d'interroger Kraken à chaque rendu de page.
    """
    symbol = symbol.upper()
    cache_key = f"kraken_price:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == 'unavailable' else Decimal(cached)

    base = _ALT_ASSET_NAMES.get(symbol, symbol)
    for quote in _PUBLIC_QUOTE_CANDIDATES:
        try:
            result = _public_request('Ticker', {'pair': f"{base}{quote}"})
        except KrakenAPIError:
            continue
        if result:
            ticker = next(iter(result.values()))
            price = Decimal(ticker['c'][0])
            cache.set(cache_key, str(price), _PRICE_CACHE_TTL)
            return price

    cache.set(cache_key, 'unavailable', _PRICE_CACHE_TTL)
    return None


def fetch_current_prices(symbols) -> tuple[dict, set]:
    """Récupère le prix courant de plusieurs symboles.

    Renvoie (prix trouvés {symbole: Decimal}, symboles non cotés sur Kraken).
    Chaque symbole est interrogé séparément : Kraken renvoie une erreur globale
    dès qu'une seule paire d'une requête groupée est inconnue.
    """
    prices = {}
    unavailable = set()
    for symbol in symbols:
        price = fetch_current_price(symbol)
        if price is None:
            unavailable.add(symbol)
        else:
            prices[symbol] = price
    return prices, unavailable


def parse_symbol_from_pair(pair: str) -> str:
    """Extrait le symbole de base (ex: 'XXBTZEUR' -> 'BTC') d'une paire Kraken."""
    base = pair
    for suffix in _QUOTE_SUFFIXES:
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    if base[:1] in ('X', 'Z') and len(base) > 3:
        base = base[1:]
    if base == 'XBT':
        base = 'BTC'
    return base.upper()


# ---------------------------------------------------------------- Trading spot

_PAIR_CACHE_TTL = 24 * 3600  # les paires changent rarement


def resolve_pair(symbol: str) -> str:
    """Résout le nom de paire Kraken (altname, ex: 'XBTUSD') pour un symbole de base.

    Teste les devises de cotation usuelles (USD puis USDT) via l'endpoint public
    AssetPairs. Résultat mis en cache 24h. Lève KrakenAPIError si aucune paire.
    """
    symbol = symbol.upper()
    cache_key = f"kraken_pair:{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    base = _ALT_ASSET_NAMES.get(symbol, symbol)
    for quote in _PUBLIC_QUOTE_CANDIDATES:
        try:
            result = _public_request('AssetPairs', {'pair': f"{base}{quote}"})
        except KrakenAPIError:
            continue
        if result:
            pair_info = next(iter(result.values()))
            altname = pair_info.get('altname') or next(iter(result.keys()))
            cache.set(cache_key, altname, _PAIR_CACHE_TTL)
            return altname

    raise KrakenAPIError(f"Aucune paire Kraken trouvée pour le symbole {symbol}.")


def add_spot_order(
    symbol: str,
    side: str,
    volume: Decimal,
    ordertype: str = 'market',
    price: Decimal | None = None,
    validate: bool = False,
) -> dict:
    """Passe un ordre spot sur Kraken (endpoint privé AddOrder).

    Args:
        symbol: symbole de base (ex: 'BTC'), résolu en paire Kraken automatiquement.
        side: 'buy' ou 'sell'.
        volume: quantité en unité de base.
        ordertype: 'market' ou 'limit'.
        price: requis pour un ordre 'limit'.
        validate: si True, Kraken valide l'ordre sans l'exécuter.

    Returns:
        {'txid': str, 'descr': str, 'pair': str}
    """
    if side not in ('buy', 'sell'):
        raise KrakenAPIError(f"Sens d'ordre invalide : {side!r} ('buy' ou 'sell' attendu).")
    if ordertype == 'limit' and price is None:
        raise KrakenAPIError("Un prix est requis pour un ordre limit.")

    pair = resolve_pair(symbol)
    payload = {
        'pair': pair,
        'type': side,
        'ordertype': ordertype,
        'volume': format(volume.quantize(Decimal('0.00000001')).normalize(), 'f'),
    }
    if price is not None:
        payload['price'] = format(price.normalize(), 'f')
    if validate:
        payload['validate'] = 'true'

    result = _private_request('AddOrder', payload)
    txids = result.get('txid') or []
    descr = result.get('descr', {}).get('order', '')
    if not txids and not validate:
        raise KrakenAPIError("Kraken n'a retourné aucun txid pour l'ordre.")
    logger.info('Kraken order placed: pair=%s side=%s volume=%s txid=%s', pair, side, volume, txids)
    return {'txid': txids[0] if txids else '', 'descr': descr, 'pair': pair}


def query_orders(txids: list[str]) -> dict:
    """Consulte le statut d'ordres par txid (endpoint privé QueryOrders)."""
    if not txids:
        return {}
    return _private_request('QueryOrders', {'txid': ','.join(txids)})


def fetch_order_fill_price(txid: str) -> Decimal | None:
    """Prix moyen d'exécution d'un ordre clôturé, ou None si non disponible."""
    orders = query_orders([txid])
    order = orders.get(txid)
    if not order:
        return None
    price = order.get('price')
    if order.get('status') == 'closed' and price:
        return Decimal(price)
    return None


def cancel_order(txid: str) -> None:
    """Annule un ordre ouvert (endpoint privé CancelOrder)."""
    _private_request('CancelOrder', {'txid': txid})
    logger.info('Kraken order cancelled: txid=%s', txid)
