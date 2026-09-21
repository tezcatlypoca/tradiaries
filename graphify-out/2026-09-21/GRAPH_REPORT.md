# Graph Report - tradiaries  (2026-09-12)

## Corpus Check
- Corpus is ~25,548 words - fits in a single context window. You may not need a graph.

## Summary
- 456 nodes · 789 edges · 70 communities (15 shown, 22 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 86 edges (avg confidence: 0.94)
- Token cost: 15,000 input · 5,200 output

## Community Hubs (Navigation)
- Kraken API Client & TP/SL Watcher
- Django Management Commands & Investment Base Model
- Credential Encryption (Fernet)
- Futures Trading Form Validation
- Admin Panels & CSV/Journal Import Scripts
- Analytics Views & Stats Computation
- Entity <-> Django Model Converters
- Page Templates (Multi-app UI)
- Live Trading Position Tracking
- Investment Stats & PWA Service Worker Serving
- Kraken Symbol Parsing & Trade Import Command
- Live/Paper Trade Mode Migration
- Django manage.py Entrypoint
- App Icon Branding (icon.svg)
- Analytics App Config
- Core App Config
- Dashboard App Config
- Futures Trading App Config
- Investment App Config
- Journal App Config
- Spot Trading App Config
- Production Deployment Plan (Render/Railway/Neon)
- Core App Package Init
- Initial Migration (core)
- SimpleInvestment Migration
- SimpleInvestment Price Fields Migration
- SimpleInvestment External Ref Migration
- FuturesTrading Strategy Field Migration
- FuturesTrading Trade Mode Migration
- ApiCredential Migration
- Concurrency Safety Migration (Nonce/is_closing)
- WatcherHeartbeat Migration
- Side Menu UI (Screenshot + Component)
- ASGI Config
- WSGI Config
- AI Discipline Coach Spin-off Idea
- Project Overview Doc

## God Nodes (most connected - your core abstractions)
1. `FuturesTrading` - 37 edges
2. `SpotTrading` - 29 edges
3. `SimpleInvestment` - 19 edges
4. `ApiCredential` - 18 edges
5. `open_position()` - 18 edges
6. `KrakenAPIError` - 14 edges
7. `Feature Trading Live — état d'implémentation` - 14 edges
8. `TradingViewTests` - 13 edges
9. `OpenPositionForm` - 13 edges
10. `SimpleInvestmentForm` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Side Menu Layout Wireframe` --conceptually_related_to--> `side-menu.html (Side Menu Component)`  [INFERRED]
  docs/image_side_menu.png → components/side-menu.html
- `import_futures_journal()` --uses--> `FuturesTrading`  [INFERRED]
  utils/import_futures_journal.py → apps/core/models.py
- `import_csv()` --uses--> `SimpleInvestment`  [INFERRED]
  utils/csv2bdd.py → apps/core/models.py
- `Render + Railway + Neon Free-Tier Deployment Topology` --conceptually_related_to--> `Tradiaries — Plan de mise en production`  [INFERRED]
  deploy/README.md → docs/tradiaries-plan-prod.md
- `spot_model_to_entity()` --uses--> `SpotTrading`  [INFERRED]
  apps/core/converters.py → apps/core/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared trading-page layout pattern (side menu + KPI cards + table + modal form)** — components_side_menu, components_kpi_cards, apps_investment_templates_investment_investment, apps_spot_trading_templates_spot_trading_spot_trading, apps_futures_trading_templates_futures_trading_futures_trading [INFERRED 0.85]
- **P0 blockers preventing LIVE trading go-live** — docs_audit_production_order_state_machine, docs_audit_production_kraken_retry_risk, docs_audit_production_concurrent_closure_risk, apps_core_trading_service, apps_core_kraken_client [EXTRACTED 1.00]
- **AI Discipline Coach roadmap across docs** — docs_project_overview_ai_discipline_coach, docs_tradiaries_plan_prod_coach_ia_spinoff, docs_tradiaries_plan_prod [INFERRED 0.85]

## Communities (70 total, 22 thin omitted)

### Community 0 - "Kraken API Client & TP/SL Watcher"
Cohesion: 0.06
Nodes (57): add_spot_order(), cancel_order(), fetch_current_price(), fetch_current_prices(), fetch_order_fill_price(), fetch_trades_history(), _get_kraken_credentials(), _http_session() (+49 more)

### Community 1 - "Django Management Commands & Investment Base Model"
Cohesion: 0.06
Nodes (24): Command, BaseCommand, Investment, Ligne unique (pk=1) : instant du dernier cycle réussi du watcher TP/SL. Stocké…, Return the average exit price when two equal-sized exits are recorded., Classe mère pour les investissements, WatcherHeartbeat, ClosePositionConcurrencyTests (+16 more)

### Community 2 - "Credential Encryption (Fernet)"
Cohesion: 0.07
Nodes (29): decrypt(), encrypt(), _fernet(), Chiffrement symétrique pour les secrets stockés en BDD (clés API des…, Chiffre une chaîne. Retourne '' si la valeur est vide (rien à chiffrer)., Déchiffre une chaîne. Retourne '' si vide ou si le déchiffrement échoue (clé…, ApiCredentialForm, Formulaire d'ajout de clé API : les champs requis dépendent de la plateforme… (+21 more)

### Community 3 - "Futures Trading Form Validation"
Cohesion: 0.09
Nodes (19): add_form_errors_to_messages(), FuturesTradingForm, Meta, Sens du trade pour la validation TP/SL (spot = toujours LONG)., SimpleInvestmentForm, SpotTradingForm, TradingForm, Trading spot sur échange (+11 more)

### Community 4 - "Admin Panels & CSV/Journal Import Scripts"
Cohesion: 0.09
Nodes (24): ApiCredentialAdmin, FuturesTradingAdmin, KrakenOrderAttemptAdmin, SimpleInvestmentAdmin, SpotTradingAdmin, KrakenNonceCounter, KrakenOrderAttempt, Meta (+16 more)

### Community 5 - "Analytics Views & Stats Computation"
Cohesion: 0.11
Nodes (22): analytics(), login_required, FuturesTrading, Trading futures avec effet de levier, _breakdown_by(), compute_futures_analytics(), compute_futures_stats(), futures_trade_pnl() (+14 more)

### Community 6 - "Entity <-> Django Model Converters"
Cohesion: 0.13
Nodes (20): futures_entity_to_model(), futures_model_to_entity(), FuturesTrading, Conversion entre dataclasses et modèles Django, Convertir un modèle Django SpotTrading en dataclass, Convertir une dataclass FuturesTrading en modèle Django, Convertir un modèle Django FuturesTrading en dataclass, Convertir une dataclass SpotTrading en modèle Django (+12 more)

### Community 7 - "Page Templates (Multi-app UI)"
Cohesion: 0.13
Nodes (3): LiveTradingConfig, AppConfig, Feature Trading Live — état d'implémentation

### Community 8 - "Live Trading Position Tracking"
Cohesion: 0.15
Nodes (17): live_positions(), Données de suivi en temps réel des positions ouvertes (spot + futures, tous…, LiveTradingViewTests, patch, TestCase, close_position(), live_trading(), open_position() (+9 more)

### Community 9 - "Investment Stats & PWA Service Worker Serving"
Cohesion: 0.15
Nodes (16): compute_investment_stats(), Stats Simple Invest : position nette par symbole (achats - ventes), valorisée…, Retourne True si le heartbeat du watcher est récent., watcher_is_healthy(), Sert le service worker à la racine (scope "/") — nécessaire pour une PWA…, service_worker(), create_investment(), delete_investment() (+8 more)

### Community 10 - "Kraken Symbol Parsing & Trade Import Command"
Cohesion: 0.15
Nodes (9): parse_symbol_from_pair(), Extrait le symbole de base (ex: 'XXBTZEUR' -> 'BTC') d'une paire Kraken., Command, BaseCommand, Commande d'import de l'historique des trades Kraken (DCA inclus) dans…, Importe les nouveaux trades de l'historique Kraken (DCA inclus) dans…, sync_kraken_trades(), Django settings for config project. Generated by 'django-admin startproject'… (+1 more)

### Community 11 - "Live/Paper Trade Mode Migration"
Cohesion: 0.33
Nodes (5): mark_existing_spot_trades_live(), mark_existing_spot_trades_paper(), Migration, Restore the pre-feature default when rolling this migration back., Preserve manually recorded historical spot trades as real trades.

### Community 12 - "Django manage.py Entrypoint"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 13 - "App Icon Branding (icon.svg)"
Cohesion: 0.83
Nodes (4): App Icon (icon.svg), Rounded Square Dark Background, Teal Uptrend Chart Line with Arrow Glyph, Tradiaries (Trading Journal App)

### Community 21 - "Production Deployment Plan (Render/Railway/Neon)"
Cohesion: 0.67
Nodes (3): Render + Railway + Neon Free-Tier Deployment Topology, Global Authorization Model (P1), Tradiaries — Plan de mise en production

## Ambiguous Edges - Review These
- `password_change_done.html` → `password_change_form.html`  [AMBIGUOUS]
  apps/dashboard/templates/registration/password_change_done.html · relation: conceptually_related_to

## Knowledge Gaps
- **17 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 222 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `password_change_done.html` and `password_change_form.html`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `FuturesTrading` connect `Analytics Views & Stats Computation` to `Kraken API Client & TP/SL Watcher`, `Django Management Commands & Investment Base Model`, `Credential Encryption (Fernet)`, `Futures Trading Form Validation`, `Admin Panels & CSV/Journal Import Scripts`, `Entity <-> Django Model Converters`, `Live Trading Position Tracking`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `Feature Trading Live — état d'implémentation` connect `Page Templates (Multi-app UI)` to `Kraken API Client & TP/SL Watcher`, `Django Management Commands & Investment Base Model`, `Futures Trading Form Validation`, `Admin Panels & CSV/Journal Import Scripts`, `Analytics Views & Stats Computation`, `Live Trading Position Tracking`, `Investment Stats & PWA Service Worker Serving`, `Kraken Symbol Parsing & Trade Import Command`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `SpotTrading` connect `Futures Trading Form Validation` to `Kraken API Client & TP/SL Watcher`, `Django Management Commands & Investment Base Model`, `Credential Encryption (Fernet)`, `Admin Panels & CSV/Journal Import Scripts`, `Analytics Views & Stats Computation`, `Entity <-> Django Model Converters`, `Live Trading Position Tracking`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `FuturesTrading` (e.g. with `futures_model_to_entity()` and `FuturesTradingForm`) actually correct?**
  _`FuturesTrading` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `SpotTrading` (e.g. with `spot_model_to_entity()` and `SpotTradingForm`) actually correct?**
  _`SpotTrading` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `SimpleInvestment` (e.g. with `SimpleInvestmentForm` and `build_chart_series()`) actually correct?**
  _`SimpleInvestment` has 9 INFERRED edges - model-reasoned connections that need verification._