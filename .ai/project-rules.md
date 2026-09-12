# Tradiaries — Project Rules

**Palier de rigueur** : Standard  
**Date d'adoption** : 2026-09-12

## Standards de code

### Python
- Type hints obligatoires (Python 3.10+)
- Docstrings Google style
- Pas de `.iterrows()` ni `.apply()` sur pandas (vectorisation)
- Logging structuré pour opérations critiques

### JavaScript
- Vanilla JS (pas de framework lourd)
- Classes CSS BEM pour composants réutilisables
- Pas d'animations coûteuses sur les éléments critiques

### CSS
- Séparation des responsabilités :
  - `style.css` : layout global + theme (variables, body, main-content, responsive)
  - `side-menu.css` : styling du menu sidebar uniquement
  - `investment.css` : composants métier (tables, forms, modals, analytics)
  - `auth.css` : pages d'authentification (indépendant)
- Variables CSS CSS pour tous les thèmes/couleurs
- Mobile-first responsive design (max-width media queries)

## Architecture

### Structure Django
```
apps/
  core/              # Modèles, services, utilitaires partagés
  dashboard/         # Page d'accueil + paramètres
  investment/        # Gestion des investissements simples
  spot_trading/      # Trading spot (LIVE/PAPER)
  futures_trading/   # Trading futures (LIVE/PAPER)
  analytics/         # Stats et performance (futures uniquement)
  journal/           # Journal des trades (futures uniquement)
  live_trading/      # Ouverture/suivi live (spot + futures)
```

### Layout global
- `body` = grid 2 colonnes : `[264px sidebar | 1fr main-content]`
- Responsive : mobile = fixed sidebar + margin-left shift
- Menu toggle + localStorage pour persistance d'état

## Conventions de nommage

### CSS classes
- `.side-menu-*` : composants menu
- `.main-content` : conteneur principal
- `.kpi-*` : cartes KPI
- `.investments-*` : tables et formulaires
- `.analytics-*` : onglets et panels
- `.investment-action-*` : badges (achat/vente, long/short, live/paper)
- `.modal-*` : modales formulaires

### Django
- Models : singulier (Investment, FuturesTrading, SpotTrading)
- Views : index + methodes helper
- Templates : `app/templates/app/view.html`
- URL patterns : `'app:view-name'` (dash-separated)

## Database

### Models clés
- `Investment` (abstract) : base spot/futures
- `SpotTrading`, `FuturesTrading` : héritent de Investment
- `SimpleInvestment` : investissements non-trading
- `FuturesTrading.trade_mode` : PAPER/LIVE
- `ApiCredential` : clés API chiffrées (Fernet)
- `KrakenOrderAttempt` : journal de réconciliation des ordres LIVE
- `WatcherHeartbeat` : health check du watcher (BDD, pas fichier)

### Champs clés
- `entry_date` : pas auto_now_add (permet import dates historiques)
- `exit_price` : quand renseigné = position clôturée
- `is_closing` : verrou concurrence pour close_position()
- `external_ref` : txid Kraken (idempotence)

## Cryptographie
- `apps/core/crypto.py` : Fernet avec SECRET_KEY
- `ApiCredential` : chiffrement symétrique des secrets

## Kraken API
- `kraken_client.py` : requêtes Kraken
- `_get_kraken_credentials()` : lit `ApiCredential` (pas .env)
- `fetch_current_price()` : cache Django 60s
- `_next_nonce()` : compteur DB (KrakenNonceCounter)
- Retry : POST non-idempotents jamais rejoués

## Tests
- Pas de `ALLOWED_HOSTS` en local (RequestFactory + appel direct)
- 19+ tests : ordre reconciliation, concurrence, stats
- `python manage.py test apps.core apps.live_trading`

## Déploiement
- **Web** : Render + Whitenoise + HTTPS obligatoire (DEBUG=False)
- **Worker** : Railway (manage.py watch_tp_sl)
- **DB** : Neon Postgres serverless (sslmode=require, CONN_MAX_AGE=0)
- **Statiques** : CompressedManifestStaticFilesStorage (prod), StaticFilesStorage (dev)
- Variables d'env : RENDER_EXTERNAL_HOSTNAME (auto-detectionRender)

## PWA
- Manifest JSON dynamique (via vue Django)
- Service Worker à `/service-worker.js` (scope global)
- Icône unique `static/icons/icon.svg`
- À générer : PNG 192×512 pour iOS/Android
