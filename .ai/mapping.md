# Tradiaries — Mapping Fichiers Clés

**Format** : Répertoire → Description succincte  
**Dernière mise à jour** : 2026-09-25

## Apps Django

### `apps/core/`
- **models.py** : Modèles principaux (Investment, SpotTrading, FuturesTrading, SimpleInvestment, ApiCredential, ApiCredentialAuditLog, KrakenNonceCounter, UserPreferences [strategy + tracked_assets], WatcherHeartbeat, KrakenOrderAttempt)
- **views.py** : Vues Dashboard, Paramètres, endpoints healthz
- **kraken_client.py** : Client Kraken (fetch_current_price, fetch_ohlc, ordres LIVE/PAPER, sync_kraken_trades)
- **vigil_client.py** (NEW 2026-09-25) : Client API Vigil (fetch_signals, bearer token, dégradation gracieuse)
- **portfolio_service.py** : Calculs stats (compute_*_stats, build_chart_series)
- **trading_service.py** : Gestion positions (open_position, close_position, check_tp_sl, live_positions)
- **forms.py** : Formulaires Investment, Spot/Futures Trading, ApiCredential
- **crypto.py** : Chiffrement Fernet (encrypt, decrypt)
- **tests.py** : Tests core (75+ tests au total ; +33 le 2026-09-22 : watcher, kraken_client, portfolio_service)

### `apps/dashboard/`
- **views.py** : Dashboard, Settings, PWA routes (manifest, service_worker), signup
- **forms.py** : SignupForm, UserStrategyForm (strategy + tracked_assets, NEW 2026-09-25)
- **templates/** : dashboard.html, login.html, signup.html, settings.html (section "Actifs suivis" NEW 2026-09-25)
- **management/commands/import_kraken_trades.py** : Import historique Kraken

### `apps/positions/` (NEW 2026-09-21)
- **views.py** : Page Positions (fusion Spot/Futures, lecture seule)
- **templates/positions.html** : Tableau filtrable, panneau détail JS
- **tests.py** : Tests isolation multi-utilisateur

### `apps/live_trading/`
- **views.py** : Page Trading, endpoints ohlc_json, vigil_signals_json (NEW 2026-09-25), positions_json, open/close_position
- **templates/live_trading.html** : Interface exchange-like (OHLC + Volume + SAR, ticket d'ordre, bandeau news Vigil)
- **forms.py** : OpenPositionForm (validation IRC)
- **tests.py** : Tests rendering, OHLC, positions, VigilSignalsJsonViewTests

### `apps/investment/`, `apps/spot_trading/`, `apps/futures_trading/`, `apps/analytics/`, `apps/journal/`
- **views.py** : Listes, filtres mode/category, stats
- **templates/** : Listes investissements, tables interactives
- **forms.py** : Formulaires création/édition

## Configuration

### `config/`
- **settings.py** : Django config, variables sécurité, DB, logging, apps
- **urls.py** : Routage global, includes apps
- **wsgi.py** : WSGI entry point

## Frontend

### `static/`
- **css/**
  - `style.css` : Layout global, variables CSS, theme, breakpoints unifiés (≤599/600-1024/>1024, 2026-09-25)
  - `side-menu.css` : Menu latéral, animations, états rail tablette/drawer mobile (2026-09-25)
  - `investment.css` : Styles investissements/positions, `.col-tablet-hide`/`.detail-row` (2026-09-25)
  - `trading.css` : Page Trading exchange-like, seuil colonne unique + hauteurs adaptatives (2026-09-25)
  - `auth.css` : Login/signup
  - `bottom-tab-bar.css` (NEW 2026-09-25) : Barre de navigation basse mobile
- **js/**
  - `side-menu.html` : Composant menu (localStorage state, 3 états mobile/tablette/desktop)
  - `row-detail-panel.js` (renommé 2026-09-25, ex `positions-detail-panel.js`) : Panneau détail générique (Positions + Trading positions ouvertes)
  - `pwa-register.js` : Enregistrement service worker
  - `vendor/lightweight-charts.standalone.production.js` : Graphiques (160KB)
- **icons/**
  - `candlestick-icon.svg` : PWA icon moderne (trading)
  - PNG générés (192×192, 512×512)

### `components/`
- `side-menu.html` : Composant menu réutilisable
- `bottom-tab-bar.html` (NEW 2026-09-25) : Barre de navigation basse mobile (Dashboard/Positions/Trading/Journal/Menu)
- `spot-trading-form.html`, `futures-trading-form.html` : Modals création/édition
- `kpi-cards.html` : Cartes KPI avec eye-toggle
- `investment-table.html` : Table interactives

## Documentation

### `.ai/`
- **project-context.md** : Vue d'ensemble, features, état courant, dépendances
- **decisions.md** : Décisions retenues, débats, suspens
- **change-log.md** : Historique chronologique par session
- **project-rules.md** : Règles projet
- **mapping.md** : Ce fichier

## Données / Docs

### `docs/`
- `tradiaries-plan-prod.md` : Plan hardening production
- `audit-production.md` : Audit sécurité/robustesse 2026-09-10 (P0 corrigés depuis, voir `prod-check-2026-09-22.md`)
- `testing-plan-2026-09-22.md` : Plan d'implémentation renforcement testing
- `prod-check-2026-09-22.md` : Rapport `/prod-check` — verdict READY WITH WARNINGS (Phase 1) / NOT READY (ouverture non contrôlée)
- `API_DOCUMENTATION.md` : Doc API Vigil (endpoints, bearer token, rate limiting, ingestion cron) — copie de référence côté Tradiaries
- `coach-ia-vers-tradiaries-2026-09-25.md` : Dossier de transfert du cadrage Coach IA (relocalisé de Vigil vers Tradiaries)
- `plan-integration-vigil-2026-09-25.md` : Plan d'implémentation du bandeau news Vigil (missions, architecture)
- `plan-responsive-tablette-2026-09-25.md` : Plan de refonte responsive tablette (diagnostic vérifié visuellement, missions, implémenté le même jour)
- `plan-responsive-smartphone-2026-09-25.md` : Plan de refonte responsive smartphone (diagnostic vérifié visuellement, missions, implémenté le même jour)
- `20MM.txt` : Script Pine Script Volume Confirmation (indicateur TradingView)

### `migrations/`
- `core/migrations/` : Migrations Invest, Investment (multi-user), timeframe, UserPreferences (0016 strategy, 0018 tracked_assets), ApiCredentialAuditLog (0017)

## Tests & CI

### GitHub
- `.github/workflows/django.yml` : Tests + collectstatic + deploy checks
- `.gitignore` : Ignores standard Python/Django

## Déploiement

### Production
- **Render** : Web service (Django + Gunicorn)
- **Railway** : Worker (watch_tp_sl command)
- **Neon** : Postgres DB serverless
- **Whitenoise** : Static files serving

### Local
- `db.sqlite3` : SQLite dev DB
- `.env` : Variables d'environnement (jamais committées)

## Gestion de projet

- `requirements.txt` : Dépendances Python
- `manage.py` : Entrée Django management
- `CLAUDE.md` : Guide projet (si créé)
