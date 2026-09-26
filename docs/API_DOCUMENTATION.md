# API Vigil - Documentation Complète

## Table des matières
1. [Aperçu](#aperçu)
2. [Tutoriels](#tutoriels)
3. [Authentification](#authentification)
4. [Définition des endpoints](#définition-des-endpoints)
5. [Status et codes d'erreur](#status-et-codes-derreur)
6. [Exemples complets](#exemples-complets)
7. [Glossaire](#glossaire)

---

## Aperçu

### Qu'est-ce que Vigil ?

**Vigil** est une API de **surveillance du marché des cryptomonnaies** qui agrège les signaux de marché provenant de multiples sources externes (blockchain on-chain, flux ETF, news, données de prix, métriques DeFi). 

L'API standardise ces données hétérogènes dans un format uniforme (`MarketSignal`) pour faciliter l'intégration par les clients comme **Tradiaries**.

### Objectif principal

Fournir une **source unique de vérité** pour les signaux de marché crypto, avec :
- ✅ Agrégation multi-sources
- ✅ Scoring intelligentdes news
- ✅ Ingestion planifiée en tâche de fond (cron), lecture instantanée depuis la BDD
- ✅ Monitoring de la santé des sources
- ✅ Isolation des pannes par source

### Stack technique
- **Framework** : Flask 3.0+
- **Validation** : Pydantic 2.6+
- **Sources de données** : cryptocurrency.cv, Cryptoast, Farside, CoinGecko, Binance, Etherscan, DefiLlama
- **Base de données** : SQLite (pour persistance et audit)

### Architecture

```
Scheduler (cron in-process, tâche de fond)
        ↓
    ┌───────────────────────────────┐
    │   Aggregator (Orchestration)  │
    │   - Fetch par groupe de       │
    │     sources (cadence)         │
    │   - Scoring                   │
    │   - Persistance               │
    └───────────────────────────────┘
        ↓
    ┌─────────────────────────────────────┐
    │        Multiple Data Sources        │
    ├──────┬──────┬──────┬──────┬─────┐
    │ News │ ETF  │ On-  │ Prices Defi │
    │      │ Flow │ Chain│      │ TVL │
    └──────┴──────┴──────┴──────┴─────┘
        ↓ (persisté)
      Base SQLite
        ↑ (lecture seule, aucun fetch live)
   API Vigil (Flask) — bearer token + rate limiting
        ↑
Client (Tradiaries)
```

---

## Tutoriels

### Démarrage rapide

#### 1. Installation et configuration

```bash
# Cloner le projet
git clone <repo-url>
cd Vigil

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# (Optionnel) Activer les sources payantes cryptocurrency.cv
export CRYPTOCURRENCY_CV_ENABLE_PAID_SOURCES=true
```

#### 2. Lancer le serveur

```bash
python src/main.py
# Serveur actif sur http://localhost:8000
```

#### 3. Tester la connexion

```bash
curl http://localhost:8000/api/health
```

### Cas d'usage : Tradiaries intégrant Vigil

**Objectif** : Récupérer tous les signaux crypto du dernier jour, traiter les signaux BTC.

```python
import requests
from datetime import datetime, timedelta, timezone

API_BASE = "http://localhost:8000/api"

# 1. Récupérer tous les signaux depuis hier
yesterday = datetime.now(timezone.utc) - timedelta(days=1)
since_param = yesterday.isoformat()

response = requests.get(
    f"{API_BASE}/signals",
    params={"since": since_param}
)
all_signals = response.json()
print(f"Signaux reçus : {all_signals['count']}")
print(f"Erreurs : {all_signals['errors']}")

# 2. Filtrer sur BTC uniquement
btc_signals = [s for s in all_signals['signals'] if s['ticker'] == 'BTC']
print(f"Signaux BTC : {len(btc_signals)}")

# 3. Analyser par source
for signal in btc_signals:
    print(f"{signal['source']} - {signal['summary']}")

# 4. Vérifier la santé du système
health = requests.get(f"{API_BASE}/health").json()
if health['status'] == 'ok':
    print("✓ Toutes les sources sont opérationnelles")
else:
    print(f"⚠ Sources dégradées : {health['sources']}")
```

### Cas d'usage : Surveiller une source spécifique

```python
# Récupérer uniquement les flux ETF Bitcoin
response = requests.get("http://localhost:8000/api/signals/etf_flow")
etf_signals = response.json()

if response.status_code == 404:
    print("Source inconnue")
elif response.status_code == 200:
    print(f"ETF signals reçus : {etf_signals['count']}")
    for signal in etf_signals['signals']:
        print(f"  - {signal['summary']}")
```

---

## Authentification

### Bearer token

L'API Vigil valide un jeton partagé sur toutes ses routes, **sauf `/api/health`** (accessible sans en-tête, pour les health checks de la plateforme d'hébergement) :

```
Authorization: Bearer <VIGIL_BEARER_TOKEN>
```

- `VIGIL_BEARER_TOKEN` est une variable d'environnement définie côté Vigil ; Tradiaries doit envoyer la même valeur en en-tête `Authorization` sur chaque appel.
- Absence ou mauvaise valeur du token → `401 Unauthorized`.
- **Mode développement local** : si `VIGIL_BEARER_TOKEN` n'est pas défini côté serveur, l'authentification est désactivée pour tous les appelants (un avertissement est loggé au démarrage). Ne pas déployer en production sans définir ce jeton.

### Rate limiting

Chaque client (identifié par son en-tête `Authorization`, ou par IP à défaut) est limité à un nombre de requêtes par minute, configurable via `VIGIL_RATE_LIMIT_PER_MINUTE` (30/min par défaut). Au-delà : `429 Too Many Requests`. `/api/health` n'est pas soumise à cette limite.

### Sécurité recommandée en complément

- ✓ TLS/HTTPS entre Tradiaries et Vigil
- ✓ Ne jamais logger le bearer token en clair côté Tradiaries

### Variables d'environnement sensibles

```bash
# Authentification et rate limiting (voir ci-dessus)
VIGIL_BEARER_TOKEN=<secret partagé avec Tradiaries>
VIGIL_RATE_LIMIT_PER_MINUTE=30

# Chemin base de données
VIGIL_DB_PATH=/data/vigil.db

# Mode debug
FLASK_ENV=development  # ou 'production'
```

---

## Définition des endpoints

### 1️⃣ GET `/api/health`

Retourne l'état de santé du système et de chaque source.

**Paramètres** : Aucun

**Réponse (200 OK)**
```json
{
  "status": "ok",
  "sources": {
    "news_aggregator": "ok",
    "news_editorial": "ok",
    "etf_flow": "ok",
    "crypto_market": "ok",
    "crypto_prices": "ok",
    "onchain_ethereum": "ok",
    "defi_tvl": "ok"
  }
}
```

**Statut possible** :
- `"ok"` : Toutes les sources sont opérationnelles
- `"degraded"` : Au moins une source a échoué récemment

**Cas d'erreur** : Aucun. L'endpoint retourne toujours 200.

**Notes** :
- Basé sur l'historique de fetch persisté en DB
- Pas d'interrogation directe des sources (très rapide)
- Les sources non encore testées apparaissent comme `"ok"`

---

### 2️⃣ GET `/api/signals`

Retourne les signaux **persistés en base**, toutes sources confondues, avec filtrage optionnel. Ne déclenche **aucun fetch live** : les données sont rafraîchies en tâche de fond par le scheduler d'ingestion (voir « Fraîcheur des données » dans le glossaire).

**Paramètres de requête** (optionnels) :
| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `ticker` | string | Filtrer par code actif (ex: BTC, ETH) | `?ticker=BTC` |
| `since` | string | Borne basse ISO8601 (incluse) sur `timestamp`. **Par défaut : dernières 24h** si absent — utiliser `since` pour accéder à un historique plus ancien | `?since=2026-09-20T10:00:00+00:00` |

**Réponse (200 OK)**
```json
{
  "signals": [
    {
      "source": "etf_flow",
      "reliability_tier": 2,
      "durability": "event",
      "ticker": "BTC",
      "timestamp": "2026-09-23T14:30:00+00:00",
      "raw_payload": { "flow_usd": 150000000 },
      "summary": "ETF Bitcoin inflows: $150M",
      "impact_score": null,
      "news_score": null
    },
    {
      "source": "news_editorial",
      "reliability_tier": 3,
      "durability": "event",
      "ticker": "ETH",
      "timestamp": "2026-09-23T13:00:00+00:00",
      "raw_payload": { "article_id": "abc123" },
      "summary": "Ethereum upgrade scheduled",
      "impact_score": null,
      "news_score": {
        "event_key": "event-0",
        "importance": { "intraday": 4, "swing": 6, "position": 8 },
        "novelty": 10,
        "source_count": 2,
        "scoring_version": "v1-heuristic"
      }
    }
  ],
  "count": 2,
  "errors": {}
}
```

**Notes** :
- `errors` est toujours `{}` sur cette route : un échec de fetch amont n'affecte pas la lecture (les signaux déjà persistés restent servis). Consulter `/api/health` pour l'état réel des sources.
- `raw_payload` retombe à `{}` si le payload brut a dépassé sa rétention courte (30 jours, purge automatique) — la version parsée (`summary`, scores, etc.) reste disponible en rétention longue.
- `news_score.importance` est un score 1-10 **par bucket de timeframe** (`intraday`/`swing`/`position`), pas une valeur unique — uniquement présent pour les signaux `news_aggregator`/`news_editorial`.

---

### 3️⃣ GET `/api/signals/<source>`

Retourne les signaux **persistés en base** d'une source unique. Comme `/api/signals`, aucun fetch live n'est déclenché.

**Paramètres** :
- `source` (path) : Clé source (ex: `etf_flow`, `news_editorial`)

**Paramètres de requête** (optionnels) :
- `ticker` : Filtrer par actif (même format que `/signals`)
- `since` : Filtrer par timestamp, même défaut 24h que `/signals`

**Reponse (200 OK)**
```json
{
  "signals": [
    {
      "source": "news_editorial",
      "reliability_tier": 3,
      "durability": "event",
      "ticker": "ETH",
      "timestamp": "2026-09-23T13:00:00+00:00",
      "raw_payload": { "article_id": "abc123" },
      "summary": "Ethereum upgrade scheduled",
      "impact_score": null,
      "news_score": {
        "event_key": "event-0",
        "importance": { "intraday": 4, "swing": 6, "position": 8 },
        "novelty": 8,
        "source_count": 1,
        "scoring_version": "v1-heuristic"
      }
    }
  ],
  "count": 1,
  "errors": {}
}
```

**Erreur : Source inconnue (404 Not Found)**
```json
{
  "error": "Unknown source: not_a_real_source"
}
```

**Note** : `source_count` est calculé une fois à l'ingestion (sur le groupe de sources co-planifiées, voir « Fraîcheur des données ») puis simplement relu ici — sa valeur est identique à celle renvoyée par `/api/signals` pour le même événement, contrairement à l'ancienne architecture où interroger une source seule limitait `source_count` à 1.

**Sources disponibles** :
| Clé | Description | Fiabilité | Durabilité |
|-----|-------------|-----------|-----------|
| `news_aggregator` | News crypto agrégées | EDITORIAL | EVENT |
| `news_editorial` | Analyses Cryptoast | EDITORIAL | EVENT |
| `etf_flow` | Flux ETF Bitcoin | QUANTITATIVE | EVENT |
| `crypto_market` | Données CoinGecko | QUANTITATIVE | EVENT |
| `crypto_prices` | Prix Binance OHLCV | QUANTITATIVE | EVENT |
| `onchain_ethereum` | Etherscan top holders | GROUND_TRUTH | EVENT |
| `defi_tvl` | DefiLlama TVL/liquidations | QUANTITATIVE | EVENT |

**Notes** :
- Retourne toujours `count` et `errors` pour cohérence
- Erreur partielle retourne 200 (pas 500)
- Isolation : si source X échoue, autres ne sont pas affectées

---

### 4️⃣ GET `/api/signals/sources_list`

Retourne la liste des **sources actuellement activées** sans les interroger.

**Paramètres** : Aucun

**Réponse (200 OK)**
```json
{
  "sources": [
    "Binance",
    "CoinGecko",
    "Cryptoast",
    "DefiLlama",
    "Etherscan",
    "Farside",
    "cryptocurrency.cv"
  ],
  "count": 7
}
```

**Notes** :
- Liste dédupliquée (plusieurs sources peuvent venir du même site)
- Triée alphabétiquement
- Utile pour un UI/dropdown de sélection
- Très rapide (pas de fetch)

---

### 5️⃣ GET `/api/internal/alerts/never-fetched`

Liste les sources actives n'ayant **jamais été fetchées** (aucune entrée dans le journal d'ingestion), distinct d'une dégradation après fonctionnement normal (déjà couverte par `/api/health`). Route interne, destinée au diagnostic (pas un endpoint de données pour Tradiaries).

**Paramètres** : Aucun

**Réponse (200 OK)**
```json
{
  "never_fetched": ["defi_tvl"],
  "count": 1
}
```

**Notes** :
- Authentification bearer requise comme le reste de l'API (pas d'exemption, contrairement à `/api/health`)
- Utile juste après le déploiement d'une nouvelle source, ou pour diagnostiquer un job de cron qui ne tourne pas

---

## Status et codes d'erreur

### Codes HTTP

| Code | Signification | Cas d'usage |
|------|---------------|-----------|
| **200** | Succès | Requête valide, données retournées |
| **401** | Non autorisé | `Authorization: Bearer` absent ou invalide (si `VIGIL_BEARER_TOKEN` configuré) |
| **404** | Non trouvé | Source inconnue dans `/api/signals/<source>` |
| **429** | Trop de requêtes | Limite `VIGIL_RATE_LIMIT_PER_MINUTE` dépassée |
| **400** | Mauvaise requête | Format paramètre invalide (ex: `since` non ISO8601) |
| **500** | Erreur serveur | Bug interne non prévu |

### Enveloppe de réponse

Tous les endpoints `/api/signals*` retournent une **enveloppe standardisée** :

```json
{
  "signals": [...],      // Tableau de MarketSignal ou vide
  "count": 0,            // Nombre entier ≥ 0
  "errors": {}           // Dict source → message d'erreur
}
```

### `errors` sur `/api/signals*` : toujours vide

Depuis le passage à l'ingestion planifiée, `/api/signals` et `/api/signals/<source>` ne font plus de fetch live : un échec de source amont **n'apparaît jamais** dans leur champ `errors` (conservé dans l'enveloppe pour compatibilité, mais vide). L'état réel des sources (échec, dégradation, jamais fetchée) se consulte via `/api/health` et `/api/internal/alerts/never-fetched`.

**Service Vigil indisponible** (panne du service lui-même, pas d'une source amont)
- HTTP 500 (ou timeout de connexion)
- Contacter l'équipe Vigil

### Messages d'erreur courants

| Message | Cause | Action |
|---------|-------|--------|
| `Unknown source: <name>` | Source inexistante | Vérifier liste via `/signals/sources_list` |
| `Unauthorized` | Bearer token absent/invalide | Vérifier l'en-tête `Authorization` |
| `Too Many Requests` | Limite de rate limiting dépassée | Réduire la fréquence d'appel, respecter `VIGIL_RATE_LIMIT_PER_MINUTE` |
| `Invalid datetime format for 'since'` | Paramètre mal formé | Utiliser ISO8601 : `2026-09-23T10:00:00+00:00` |

---

## Exemples complets

### Exemple 1 : Client Python simple

```python
import requests
from datetime import datetime, timezone

class VigilClient:
    def __init__(self, base_url="http://localhost:8000/api", bearer_token=None):
        self.base_url = base_url
        self._headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    def health(self):
        """Vérifier santé du système (route non protégée, pas besoin de token)"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def get_signals(self, ticker=None, since=None):
        """Récupérer signaux avec filtrage optionnel"""
        params = {}
        if ticker:
            params["ticker"] = ticker.upper()
        if since:
            params["since"] = since.isoformat() if isinstance(since, datetime) else since
        
        response = requests.get(f"{self.base_url}/signals", params=params, headers=self._headers)
        response.raise_for_status()  # 401/429 lèvent ici
        data = response.json()
        return data["signals"], data["errors"]
    
    def get_source_signals(self, source, ticker=None):
        """Récupérer signaux d'une source spécifique"""
        params = {}
        if ticker:
            params["ticker"] = ticker.upper()
        
        response = requests.get(
            f"{self.base_url}/signals/{source}",
            params=params,
            headers=self._headers,
        )
        if response.status_code == 404:
            raise ValueError(f"Source unknown: {source}")
        response.raise_for_status()
        
        data = response.json()
        return data["signals"], data["errors"]
    
    def sources(self):
        """Lister sources disponibles"""
        response = requests.get(f"{self.base_url}/signals/sources_list", headers=self._headers)
        return response.json()["sources"]


# Utilisation
client = VigilClient(bearer_token="<VIGIL_BEARER_TOKEN>")

# Vérifier santé
health = client.health()
print(f"Status: {health['status']}")

# Récupérer signaux BTC du jour
from datetime import timedelta
today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
signals, errors = client.get_signals(ticker="BTC", since=today)
print(f"BTC signals: {len(signals)}")

# Analyser flux ETF
etf_signals, etf_errors = client.get_source_signals("etf_flow", ticker="BTC")
for signal in etf_signals:
    print(f"ETF: {signal['summary']}")
```

### Exemple 2 : Intégration Tradiaries (pseudo-code)

```python
# Dans le système Tradiaries
from vigil_client import VigilClient
from tradiaries.models import Signal as TradiariesSignal

vigil = VigilClient(base_url=config.VIGIL_API_URL, bearer_token=config.VIGIL_BEARER_TOKEN)

def sync_vigil_signals():
    """Synchroniser signaux Vigil → Tradiaries"""
    
    # 1. Vérifier santé
    health = vigil.health()
    if health['status'] != 'ok':
        logger.warning(f"Vigil degraded: {health['sources']}")
    
    # 2. Récupérer signaux récents (errors est toujours {} : les échecs de
    #    fetch amont sont visibles via health['sources'] ci-dessus, pas ici)
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    vigil_signals, _ = vigil.get_signals(since=since)
    
    # 3. Transformer en modèle Tradiaries
    tradiaries_signals = []
    for vigil_signal in vigil_signals:
        signal = TradiariesSignal(
            source="vigil",
            vigil_source=vigil_signal['source'],
            ticker=vigil_signal['ticker'],
            timestamp=vigil_signal['timestamp'],
            message=vigil_signal['summary'],
            confidence=_map_reliability_to_confidence(vigil_signal['reliability_tier']),
            raw_data=vigil_signal
        )
        tradiaries_signals.append(signal)
    
    # 4. Persister dans Tradiaries
    db.bulk_insert_signals(tradiaries_signals)
    logger.info(f"Synced {len(tradiaries_signals)} signals from Vigil")

def _map_reliability_to_confidence(tier):
    """1 = GROUND_TRUTH → high, 3 = EDITORIAL → medium"""
    return {1: 'high', 2: 'medium', 3: 'low'}.get(tier, 'low')
```

### Exemple 3 : Requêtes cURL

```bash
TOKEN="<VIGIL_BEARER_TOKEN>"

# Health check (pas de token nécessaire)
curl http://localhost:8000/api/health | jq .

# Tous les signaux (dernières 24h par défaut)
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/signals" | jq '.count'

# Signaux BTC depuis hier
SINCE=$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S%z)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/signals?ticker=BTC&since=$SINCE" | jq '.signals | length'

# Signaux ETF flow
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/signals/etf_flow" | jq '.signals[0] | {ticker, summary}'

# Sources actives
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/signals/sources_list" | jq '.sources | sort'

# Sources jamais fetchées (diagnostic)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/internal/alerts/never-fetched" | jq .

# Gestion erreurs
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/signals/not_a_source" | jq .
# → {"error": "Unknown source: not_a_source"}

# Token manquant/invalide
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/signals"
# → 401 (si VIGIL_BEARER_TOKEN est configuré côté serveur)
```

---

## Glossaire

### Concepts de base

| Terme | Définition |
|-------|-----------|
| **Signal** | Observation/événement significatif du marché crypto standardisé en `MarketSignal` |
| **Ticker** | Code actif (ex: BTC, ETH, SOL) ou `null` si métrique agrégée |
| **Source** | Connecteur de données (ex: `etf_flow`, `crypto_prices`) |
| **Site** | Service tiers (ex: Binance, CoinGecko) |
| **Timestamp** | Horodatage UTC ISO8601 du signal |

### MarketSignal (Structure de données)

**Champ** | **Type** | **Requis** | **Description**
|---------|--------|-----------|----------|
| `source` | enum SignalSource | ✓ | Origine du signal |
| `reliability_tier` | int (1-3) | ✓ | Niveau de fiabilité |
| `durability` | enum | ✓ | Fenêtre de pertinence |
| `ticker` | string | ✗ | Code actif (ex: BTC) ou null |
| `timestamp` | datetime | ✓ | Horodatage UTC |
| `raw_payload` | object | ✓ | Données brutes de la source |
| `summary` | string | ✗ | Résumé lisible court |
| `impact_score` | int (1-10) | ✗ | Score d'impact (réservé) |
| `news_score` | object | ✗ | Score news multi-dim (news only) |

### Niveaux de fiabilité (ReliabilityTier)

| Niveau | Valeur | Exemple | Interprétation |
|--------|--------|---------|-----------------|
| **GROUND_TRUTH** | 1 | Transactions on-chain | Données officielles, aucune interprétation |
| **QUANTITATIVE** | 2 | Prix agrégés, TVL | Métriques calculées par tiers |
| **EDITORIAL** | 3 | News, analyses | Opinion/analyse humaine |

**→ Utiliser pour évaluer confiance dans la donnée**

### Durabilité (SignalDurability)

| Type | Durée typ. | Exemple |
|------|-----------|---------|
| **EVENT** | Heures/jours | News, prix, transactions |
| **STRUCTURAL** | Semaines/mois | Changements protocole, métriques long-terme |

**→ Utiliser pour expiration/pertinence contextuelle**

### News Score (pour signaux NEWS_*)

Multi-dimensional scoring des news :
```json
{
  "importance": 8,    // 1-10 : pertinence pour trader
  "novelty": 7,       // 1-10 : info nouvelle
  "source_count": 3   // Nombre de sources mentionnant
}
```

**→ Aider filtrer/classer news**

### Enveloppe API

Structure standardisée de toute réponse `/api/signals*` :
- `signals` : Tableau MarketSignal
- `count` : Nombre de signaux (int ≥ 0)
- `errors` : Dict source → message erreur

**→ Permettre gestion erreurs partielles**

### Fraîcheur des données (ingestion planifiée)

Vigil ne fait plus de fetch live sur les requêtes API : un scheduler in-process rafraîchit chaque source en tâche de fond, à une cadence fixe par groupe de sources (pas une fenêtre de cache par requête) :
- **Cadence rapide** (~2 min) : `crypto_prices`, `crypto_market`
- **Cadence standard** (~10 min) : `news_aggregator`, `news_editorial`, `etf_flow`, `defi_tvl`, `onchain_ethereum`

`/api/signals*` lit toujours l'état le plus récent en base — la fraîcheur perçue par Tradiaries dépend uniquement de la cadence ci-dessus, pas de la fréquence de ses propres appels. **Aucune action de cache côté Tradiaries n'est nécessaire pour protéger les sources amont** : plusieurs appels simultanés de plusieurs utilisateurs Tradiaries lisent tous la même base, sans jamais déclencher d'appel supplémentaire vers CoinGecko/Etherscan/etc.

**→ Pas de patience à observer entre requêtes côté client : la lecture est toujours instantanée**

### Sources de données principales

| Source | Site | Type | Fiabilité | Phase |
|--------|------|------|-----------|-------|
| `news_aggregator` | cryptocurrency.cv | News | EDITORIAL | 0 |
| `news_editorial` | Cryptoast | News | EDITORIAL | 0 |
| `etf_flow` | Farside | Flow | QUANTITATIVE | 0 |
| `crypto_market` | CoinGecko | Marché | QUANTITATIVE | 1 |
| `crypto_prices` | Binance | Prices | QUANTITATIVE | 1 |
| `onchain_ethereum` | Etherscan | On-chain | GROUND_TRUTH | 1 |
| `defi_tvl` | DefiLlama | DeFi | QUANTITATIVE | 1 |

**Phase 1** = Déploiement 2026-09-23, remplace partiellement crypto.cv payant

---

## Annexe : Variables d'environnement

```bash
# Obligatoires en production
FLASK_ENV=production          # ou 'development'
VIGIL_BEARER_TOKEN=<secret partagé avec Tradiaries>  # sinon auth désactivée (mode dev)

# Sécurité
VIGIL_RATE_LIMIT_PER_MINUTE=30  # défaut si absent

# Base de données
VIGIL_DB_PATH=/var/lib/vigil/vigil.db

# Sources payantes (crypto.cv, désactivées par défaut)
CRYPTOCURRENCY_CV_ENABLE_PAID_SOURCES=true
```

## Support et contact

- **Issues** : Créer ticket dans repo Vigil
- **Slack** : Channel #vigil-api
- **Urgent** : Contacter équipe data

---

**Dernière mise à jour** : 24 septembre 2026  
**Version API** : 1.1 (bearer token, rate limiting, ingestion planifiée par cron)  
**Statut** : Production (Phase 1)
