# Tradiaries — Project Context

**Dernière mise à jour** : 2026-09-22  
**État générale** : Fonctionnel en dev, PWA avec icon candlestick, UI trading refondue (drag & drop TP/SL fiabilisé, SAR corrigé, graphiques synchronisés), page Positions limitée aux positions clôturées, multi-utilisateur opérationnel, audit trail clés API, suite de tests renforcée (watcher/kraken_client/portfolio_service/dashboard), 85 tests ✅

## Cadrage

**Tradiaries** est une application Django personnelle de suivi de trading et d'investissements en cryptomonnaies. Elle gère :
- Investissements simples (achat/vente USDT)
- Trading spot sur Kraken (LIVE/PAPER)
- Trading futures (LIVE/PAPER) avec journal et analytics
- Suivi du portefeuille via dashboard
- Watcher TP/SL pour gestion automatique des positions

**Stack** : Python 3.11 + Django 5.2 + Vanilla JS + CSS DeFi dark-theme  
**Utilisateurs** : Multi-utilisateur depuis le 2026-09-14 (isolation des données par compte + inscription publique ; voir `decisions.md` "Multi-utilisateur"). Historique de données conservé sous le compte `samsan`.  
**Déploiement** : Render (web) + Railway (worker) + Neon (DB)

---

## État courant

### Fonctionnalités implémentées ✅

#### Core
- ✅ Modèles Investment/SpotTrading/FuturesTrading avec héritage
- ✅ Prix live Kraken (cache 60s)
- ✅ Import CSV legacy (SimpleInvestment)
- ✅ Import Notion futures journal

#### Dashboard
- ✅ KPI cards (Portfolio Value, Capital, PnL Global) — blurred toggle via localStorage
- ✅ Graphique du portfolio (cost basis cumulé par catégorie, pas mark-to-market)
- ✅ Filtres timeline (1D/1W/1M/1Y/All)
- ✅ Filtres catégorie (Investment/Spot/Futures/All)

#### Investissements
- ✅ Page lisible avec import auto Kraken
- ✅ Messages Django affichés

#### Trading Spot
- ✅ Liste des positions
- ✅ Mode LIVE/PAPER/ALL avec tabs
- ✅ KPI par mode

#### Trading Futures
- ✅ Liste des positions + champ strategy (Notion)
- ✅ Mode LIVE/PAPER/ALL avec tabs
- ✅ KPI par mode
- ✅ Trade mode dans formulaire

#### Analytics (Futures uniquement)
- ✅ Tabs LIVE/PAPER
- ✅ Stats : Win rate, Profit factor, R moyen, best/worst trade
- ✅ Ventilations : par stratégie, symbole, ressenti, direction
- ✅ Support `None` pour stats indisponibles

#### Journal (Futures uniquement)
- ✅ Liste chronologique avec PnL attaché dynamiquement
- ✅ Filtres GET : mode, strategy, symbol

#### Trading Live
- ✅ Ouverture spot PAPER/LIVE, futures PAPER
- ✅ Validation IRC 4h (regime, SAR, volume profile) pour LIVE
- ✅ Suivi JSON et watcher TP/SL

#### Sécurité/Audit (2026-09-10)
- ✅ P0-1 : KrakenOrderAttempt journal de réconciliation
- ✅ P0-2 : KrakenNonceCounter + pas de retry POST
- ✅ P0-3 : is_closing pour concurrence close_position()
- ✅ P1 : Watcher heartbeat en BDD (WatcherHeartbeat)
- ✅ P1 : Isolation erreurs watcher (par position)
- ✅ P1 : Clé API unique par plateforme
- ✅ P1 : HTTPS obligatoire (DEBUG=False)

#### UI Polish (2026-09-11)
- ✅ Chart dashboard : style modernisé, couleurs DeFi
- ✅ Menu : font-size/weight augmenté
- ✅ Eye toggle (password + KPI)
- ✅ PWA : manifest, service worker, registre PWA

#### PWA Icon Candlestick (2026-09-12)
- ✅ SVG candlestick (moderne, OHLC + uptrend arrow)
- ✅ PNG 192×192 + 512×512 générés (cairosvg)
- ✅ Manifest updated (theme_color #10b981, purpose maskable)
- ✅ Tous les templates référencent l'icon candlestick

#### Responsive (2026-09-12)
- ✅ Tablet (769–1024px) : 2-col KPI grid, sidebar réduit
- ✅ Mobile (<600px) : 1-col grid, table→card layout, modales fullscreen
- ✅ Touch-friendly : padding augmenté, font 16px sur inputs

#### Menu & Layout (2026-09-12)
- ✅ Persistance d'état menu via localStorage
- ✅ Pas de flicker au rechargement
- ✅ Menu replié n'occulte pas le contenu (margin-left)
- ✅ Refacto CSS : style.css (layout global) + side-menu.css (styling menu)

#### PWA Chrome Installability (2026-09-13)
- ✅ Service worker handles navigations (network-first for HTML pages)
- ✅ Service worker deployed at root scope (/) with Service-Worker-Allowed header
- ✅ Manifest complete with 3 icons (SVG + PNG 192×512)
- ✅ PWA registration uses updateViaCache: 'none' for immediate updates
- ✅ All endpoints decorated with @never_cache for service worker freshness
- ✅ PWA tests added to integration suite (2/2 passing)

#### Multi-utilisateur (2026-09-14)
- ✅ Chaque modèle métier (SimpleInvestment, SpotTrading, FuturesTrading, ApiCredential, KrakenOrderAttempt, KrakenNonceCounter) a un propriétaire (`user`)
- ✅ Toutes les vues filtrent/rattachent par `request.user` ; `get_object_or_404` scopé par utilisateur (faille IDOR corrigée)
- ✅ Page d'inscription publique (`accounts/signup/`), connexion automatique après inscription
- ✅ Clés Kraken, nonce, et positions LIVE scopées par utilisateur (watcher global, clés par propriétaire)
- ✅ Tests d'isolation multi-utilisateur (`MultiUserIsolationTests`, 5 tests) + suite complète (26 tests) verte
- ⏳ Module de coaching IA : volontairement non développé (prochaine étape, hors périmètre de cette session)

#### Time frame (2026-09-14)
- ✅ Champ `timeframe` (texte libre, ex: 15min/4h/1D) ajouté au modèle mère `Investment` — hérité par `SpotTrading`/`FuturesTrading` (pas `SimpleInvestment`)
- ✅ Migration `core.0015` appliquée en local, formulaires + modals Spot/Futures mis à jour
- 🟡 Migration production (Neon) : PAS encore appliquée — se fait automatiquement au prochain déploiement Render (build command inclut `migrate`), ou manuellement si besoin (voir marche à suivre transmise à l'utilisateur)

#### Positions (2026-09-21, mise à jour même session)
- ✅ Nouvelle app `apps/positions` : fusion Spot/Futures en page unique, lecture seule (aucune création/clôture ici)
- ✅ Onglets Spot/Futures, filtres par mode (LIVE/PAPER), KPI recalculées côté serveur
- ✅ Panneau détail JS en lecture seule, suppression déléguée aux endpoints existants
- ✅ Menu mis à jour : lien "📂 Positions" unique
- ✅ N'affiche plus que les positions **clôturées** (`exit_price__isnull=False`) ; les positions ouvertes ne s'affichent plus que sur la page Trading (décision explicite : la page Investissements/`SimpleInvestment` reste inchangée, pas de notion d'ouvert/fermé pour ce modèle)

#### Trading UI (2026-09-21, plusieurs passes)
- ✅ Refonte page Trading (exchange-like) : dropdown d'actifs (au lieu de liste de boutons)
- ✅ Graphique OHLC : hauteur 420px → 480px, comble largeur entière (grid 3col → 2col)
- ✅ Graphique Volume : histogramme coloré (vert haussier, rouge baissier) + ligne Moyenne Mobile 20 superposée
- ✅ Indicateur SAR (Stop And Reverse) : affiché en points disjoints (style TradingView, `pointMarkersVisible`) ; algorithme Wilder corrigé (l'extreme point `ep` était figé pendant la poursuite de tendance, causant une convergence vers une asymptote horizontale fixe — voir `change-log.md`)
- ✅ Graphique prix et graphique volume/MM20 synchronisés horizontalement (pan/zoom bidirectionnel via `subscribeVisibleLogicalRangeChange`)
- ✅ Tests : 1 test mis à jour pour nouveau sélecteur d'actif

#### Drag & drop TP/SL (2026-09-21, 2 correctifs successifs)
- ✅ Cause racine #1 : `priceScale().priceToCoordinate()/coordinateToPrice()` n'existent pas sur `IPriceScaleApi` (seulement sur `ISeriesApi`) → `TypeError` silencieuse bloquant tout drag. Corrigé via `candleSeries.priceToCoordinate()/coordinateToPrice()` directement.
- ✅ Cause racine #2 (bug intermittent restant) : le clic-glissé simple entrait en concurrence avec le pan/zoom natif de lightweight-charts (`handleScroll`/`handleScale`, actifs par défaut). Résolu par un key binding : clic-glissé simple = navigation native (pan/zoom), **Maj + clic-glissé** = déplacement de ligne Entrée/TP/SL (avec `handleScroll`/`handleScale` désactivés temporairement pendant le geste).
- ✅ Vérifié manuellement en navigateur (serveur de dev + compte de test temporaire) : pan simple n'altère plus TP/SL, Maj+glissé déplace correctement, aucune erreur console.

#### Testing (2026-09-22)
- ✅ `WatchTpSlCommandTests` (4 tests) : commande `watch_tp_sl.py` (`--once`, heartbeat, `--interval`)
- ✅ `KrakenClientTests` (15 tests) : `add_spot_order`, `query_orders`, `fetch_order_fill_price`, `cancel_order`, `_private_request` — mocks haut niveau uniquement
- ✅ `PortfolioServiceTests` (10 tests) : stats investment/spot/futures/global, analytics, chart series, isolation multi-utilisateur
- ✅ 8 nouveaux tests `apps/dashboard/tests.py` : dashboard, signup, save_strategy, création/suppression `ApiCredential` (isolation)
- 🟡 Bug connu découvert (non corrigé, voir `change-log.md` 2026-09-22) : caractère `✓` non encodable en cp1252 dans `watch_tp_sl.py` — cycle réussi mal classé "échec" sur console Windows par défaut (sans impact prod, Railway = Linux/UTF-8)
- **Hors périmètre (décision gelée)** : ordres futures LIVE via API Kraken Futures — voir `decisions.md`, rejetée le 2026-09-22

### À faire ⏳

#### Responsive mobile (< 600px)
- 🟡 Portfolio chart responsive (ajuster hauteur/polices)
- 🟡 Test complet sur vrais appareils (tablette/téléphone)

#### Futures Trading
- 🟡 Affichage du champ `strategy` dans la table futures_trading.html

#### Analytics/Journal
- 🟡 Django messages sur ces pages (actuellement seule investment l'affiche)

#### Déploiement
- 🟡 Test complet Render + Railway + Neon
- 🟡 Vérifications health checks watcher
- 🔴 Committer/merger le travail de la session (audit trail, migration `0017`, tests renforcés) — rien n'est déployé tant que non mergé sur `prod`
- 🔴 Trancher l'inscription publique vs invite-only avant toute exposition non contrôlée (voir Problèmes connus / `decisions.md` en suspens)

---

## Statut de préparation production (2026-09-22)

**Verdict `/prod-check`** : 🟠 READY WITH WARNINGS pour Phase 1 (personnel) — 🔴 NOT READY pour ouverture à des utilisateurs non explicitement invités. Rapport complet : `docs/prod-check-2026-09-22.md`.

- Les 3 P0 de l'audit du 2026-09-10 (`docs/audit-production.md`) sont corrigés (machine d'états ordres, retry désactivé, verrou clôture atomique).
- Isolation multi-utilisateur vérifiée exhaustivement (grep sur tous les `views.py`) : aucune fuite trouvée.
- `check --deploy`, `makemigrations --check`, suite complète (85 tests) : tous propres.
- Bloquants restants : voir "Problèmes connus" ci-dessous (B1 travail non commité, B2 signup public).

## Problèmes connus

### Résolus cette session (2026-09-13)
- ✅ **Menu replié recouvrait le contenu (2e fix)** → Unified CSS geometry for both collapsed paths (layout-driven + click-driven)
- ✅ **Service worker not handling navigations** → Implemented network-first strategy for Chrome PWA installability
- ✅ **PWA install prompt absent** → Diagnosed: icons should be collected by Render buildpack, diagnostic tool created

### Résolus session précédente (2026-09-12)
- ✅ **Menu replié recouvrait le contenu (1re fix)** → Fixed avec `margin-left: calc(64px - 264px)`
- ✅ **Menu s'ouvrait après clique tabs** → Fixed avec localStorage initial setup sans animation
- ✅ **CSS désorganisé** → Refacto : layout global dans `style.css`, menu styling dans `side-menu.css`
- ✅ **Site blanc** → Fixed : import `style.css` dans tous les templates

### Trouvés cette session (2026-09-22, non corrigés)
- 🔴 **Inscription publique contredit le modèle "invite-only"** de la décision de sécurité Fernet — voir `decisions.md` en suspens et `docs/prod-check-2026-09-22.md`.
- 🟡 **`watch_tp_sl.py`** : un cycle réussi peut être mal classé "échec" sur console Windows (cp1252) à cause d'un caractère `✓` — sans impact prod (Railway = Linux/UTF-8). Voir `change-log.md` 2026-09-22 (TESTING).
- 🟡 Pas de protection anti-brute-force sur login/signup ; pas de monitoring/alerting (Sentry ou équivalent) — requis avant Phase 2, toujours absents.

### En attente
- ❓ PWA install prompt en production : Vérifier que PNG icons sont accessibles via manifest URLs (à tester après push Render)
- ❓ `position: fixed` menu mobile peut pas scrollable si beaucoup de liens (15+ items)
- ❓ Graphique chart pas responsive en très petit (< 300px hauteur)
- ❓ iOS Safari PWA install : valider sur appareil réel (PNG 192/512 en place, test requis)

---

## Dépendances critiques

### External
- **Kraken API** : public Ticker (fetch_current_price), private (ordres LIVE)
- **Notion** (optionnel) : export CSV journal futures

### Internal
- **apps/core/portfolio_service.py** : cœur des calculs (stats + séries chart)
- **apps/core/trading_service.py** : ordres LIVE/PAPER + TP/SL
- **static/css/style.css** : toutes les pages dépendent des variables CSS racine
- **static/js/side-menu.html** (composant) : localStorage persistence menu

---

## Checklist déploiement production

- [x] Générer logo + PNG icônes (candlestick)
- [x] Service worker handles navigations (Chrome installability)
- [x] PWA endpoints hardened (@never_cache, Service-Worker-Allowed header)
- [ ] Push code changes to Render (CSS menu fix + SW improvements)
- [ ] Verify PNG icons accessible in prod (diagnose_pwa_prod.py after deploy)
- [ ] Test PWA install on iOS/Android réels après vérification icons
- [x] HTTPS Render configuré + CSRF_TRUSTED_ORIGINS
- [x] Railway : mêmes vars de sécurité que Render
- [x] Neon DB : backup configuré
- [ ] Kraken API clé en ApiCredential (via page Settings)
- [ ] Watcher démarré sur Railway
- [ ] Health checks Render + Sentry logs
