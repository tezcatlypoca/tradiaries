# Tradiaries — Change Log

**Format** : ISO 8601 YYYY-MM-DD | Catégorie | Description courte | Fichiers modifiés  
**Dernière entrée** : 2026-09-13

---

## 2026-09-13 (Session 3) | BUG FIX + PWA | Menu geometry unified, service worker navigate handler, PWA diagnostics

### Bugs corrigés
1. **CSS menu collapsed = black band (FIXED)**
   - Cause : Deux chemins différents appliquaient des géométries différentes au contenu replié
   - Root cause 1 : localStorage restore appliquait `margin-left: calc(64px - 264px)` (négatif)
   - Root cause 2 : click-driven close utilisait `grid-column` spanning sans margin-left en desktop
   - Solution : Unifié `.side-menu.hidden ~ .main-content` + `.main-content.expanded` → `width: calc(100% - var(--sidebar-collapsed-width))` + `margin-left: var(--sidebar-collapsed-width)` (64px)
   - Impact : Menu replié n'occulte plus le contenu (left=64, right=viewport sur desktop/mobile)

2. **Service worker ne gère pas les navigations (FIXED)**
   - Cause : Original code skipped navigation requests : `if (request.mode === 'navigate') { return; }`
   - Impact : Chrome PWA installability criterion échoue (SW doit gérer ≥1 navigation)
   - Solution : Implémenté network-first strategy pour les pages HTML (fetch server → cache on success → fallback offline)
   - Impact : Pages jamais servies depuis cache en online (network toujours vérifié en premier)

3. **PWA install prompt absent en production (DIAGNOSED)**
   - Suspected cause : PNG icons (candlestick-icon-192.png, 512.png) potentially not collected en Render buildpack
   - Verification : Local `collectstatic --dry-run` confirme les 3 icônes (SVG + 2 PNG) seront incluses
   - Diagnostic tool créé : `diagnose_pwa_prod.py` (timeout en prod, Render/Cloudflare issue)
   - Next step : After deployment, if install prompt still missing → Run `python manage.py collectstatic` on Render dyno

### Code changes
- `static/css/style.css` : Unified menu geometry (both collapsed paths)
- `static/js/service-worker.js` : Network-first handler for navigations + cache-first for /static/
- `static/js/pwa-register.js` : Added `{ scope: '/', updateViaCache: 'none' }` + forced `.update()` call
- `apps/dashboard/views.py` : Added `@never_cache`, `@require_GET` decorators; added `Service-Worker-Allowed: /` header
- `apps/dashboard/templates/pwa/manifest.webmanifest` : Verified manifest is complete (3 icons, scope, display standalone)
- `apps/dashboard/tests.py` : Added 2 PWA integration tests (service-worker headers, manifest scope)
- `diagnose_pwa_prod.py` [NEW] : Diagnostic script to verify PWA icons accessibility in production

### Tests
- ✅ 21/21 Django integration tests passing (apps.dashboard, apps.core, apps.live_trading)
- ✅ PWA manifest validation : All Chrome installability requirements met locally
- ✅ CSS geometry verified : Desktop (1280×720) + mobile (390×844) both left=64, right=viewport
- ✅ Service worker active/running through page reload with proper scope
- ✅ Django system check passed

### Deployment readiness
- ✅ All code changes tested locally
- ✅ PNG icons included in collectstatic dry-run
- ✅ Service worker hardened for Chrome installability
- ⏳ Production verification : icons accessible at manifest URLs (to be verified after Render deploy)

### Files ready for production push
1. static/css/style.css (menu geometry)
2. static/js/service-worker.js (navigate handler)
3. static/js/pwa-register.js (updateViaCache option)
4. apps/dashboard/views.py (decorators/headers)
5. apps/dashboard/tests.py (PWA tests)

---

## 2026-09-12 (Session 2) | PWA ICON | Intégration icône candlestick (SVG + PNG 192/512)

### Changements PWA
1. **Nouvelle icône candlestick**
   - Créé : `static/icons/candlestick-icon.svg` (SVG modernisé avec chandelles OHLC + flèche uptrend)
   - Généré : PNG 192×192 et 512×512 via script `utils/generate_pwa_icons.py` (cairosvg)
   - Couleurs : Dark theme (#080c10 bg, #10b981 green, #ef4444 red)

2. **Mise à jour manifest PWA**
   - Fichier : `apps/dashboard/templates/pwa/manifest.webmanifest`
   - Ajout icônes PNG (192, 512) au manifest pour installabilité iOS/Android
   - Changement `theme_color` : `#080c10` → `#10b981` (vert Tradiaries)
   - Support `purpose: "maskable"` pour icône adaptative (512px)

3. **Mise à jour tous les templates**
   - Changé : `apple-touch-icon` de `icon.svg` → `candlestick-icon.svg` (8 fichiers)
   - Fichiers : dashboard.html, analytics.html, futures_trading.html, investment.html, journal.html, live_trading.html, spot_trading.html, login.html

4. **Utilitaire de génération**
   - Créé : `utils/generate_pwa_icons.py` pour générer PNG depuis SVG
   - Dépendance : cairosvg (installé via pip)
   - Usage : `python utils/generate_pwa_icons.py`

### Checklist PWA icon
- ✅ SVG candlestick créé (512×512)
- ✅ PNG 192×192 généré
- ✅ PNG 512×512 généré (maskable)
- ✅ Manifest PWA mis à jour
- ✅ Tous les templates référencent la nouvelle icône
- ✅ Django check sans erreurs

### Tests
- ✅ `python manage.py check` : System OK
- ⏳ PWA install test iOS/Android (à faire sur appareil réel)
- ⏳ Vérifier affichage icône sur écran d'accueil (app drawer)

### Bloquage levé
- 🟢 Logo & icônes PWA fonctionnels (candlestick)
- 🟡 Installabilité PWA complète (PNG en place, test réel requis)

---

## 2026-09-12 | BUG FIX + REFACTO CSS | Menu replié couvre le contenu, flicker localStorage, CSS désorganisé

### Bugs corrigés
1. **Menu replié occulte le contenu** (desktop + mobile)
   - Cause : Pas de `margin-left` en desktop pour décaler le contenu quand `.side-menu.hidden`
   - Fix : CSS `.side-menu.hidden ~ .main-content { margin-left: calc(64px - 264px); }` dans `style.css`
   - Impact : Contenu visible en permanence, peu importe l'état du menu

2. **Menu s'ouvre/ferme rapidement après clique sur tabs**
   - Cause : Script d'initialisation localStorage s'exécutait APRÈS le rendu du HTML
   - Cause 2 : Pas de classe `.visible` appliquée au bouton toggle lors de l'initialisation
   - Fix : Script IIFE immédiate avant DOMContentLoaded + classe `.initializing` pour désactiver animations au démarrage
   - Fix 2 : Ajout de `menuToggle.classList.add('visible')` quand menu fermé au démarrage
   - Impact : Pas de flicker, état menu persistent et cohérent

3. **Site blanc au chargement**
   - Cause : `style.css` n'était pas importé dans les templates (contient les variables CSS)
   - Fix : Ajouter `<link rel="stylesheet" href="{% static 'css/style.css' %}">` AVANT `side-menu.css`
   - Fichiers modifiés : dashboard.html, investment.html, spot_trading.html, futures_trading.html, analytics.html, journal.html, live_trading.html

### Refacto CSS (architecture)
- **Problème** : Tout le layout global mélangé dans `side-menu.css` → dépendances circulaires, bugs d'état
- **Solution** : Créer `style.css` avec layout global, garder `side-menu.css` pour styling menu uniquement
- **Contenu `style.css`** :
  - Variables CSS `:root`
  - Imports fonts Google
  - Grid body + `main-content`
  - `.main-content` avec `margin-left` transition pour menu replié/déplié
  - KPI cards, dashboard, buttons
  - Media queries tablet (769–1024px) + mobile (<600px)
  - Scrollbar styling
- **Contenu `side-menu.css`** (nettoyé) :
  - `.side-menu` + `.side-menu.hidden` + `.side-menu.initializing`
  - `.menu-toggle`, `.menu-header`, `.menu-list`, `.submenu`
  - Animations du menu
  - Scrollbar du menu uniquement
- **Fichiers supprimés de side-menu.css** : dashboard-container, kpi-grid, portfolio-chart, buttons, material-icons

### Responsive improvements
- **Tablet (769–1024px)** : KPI grid 2 colonnes, sidebar réduit 240px
- **Mobile (<600px)** : Persistance menu via localStorage respectée
- **Touch-friendly** : Padding augmenté sur KPI cards, buttons fullwidth

### Files modified
- `static/css/style.css` [NEW] — Layout global + theme
- `static/css/side-menu.css` [REFACTORED] — Menu styling only
- `components/side-menu.html` [FIXED] — Script IIFE + class `.visible` on toggle init
- `apps/dashboard/templates/dashboard/dashboard.html` [UPDATED] — Added style.css import
- `apps/investment/templates/investment/investment.html` [UPDATED] — Added style.css import
- `apps/spot_trading/templates/spot_trading/spot_trading.html` [UPDATED] — Added style.css import
- `apps/futures_trading/templates/futures_trading/futures_trading.html` [UPDATED] — Added style.css import
- `apps/analytics/templates/analytics/analytics.html` [UPDATED] — Added style.css import
- `apps/journal/templates/journal/journal.html` [UPDATED] — Added style.css import
- `apps/live_trading/templates/live_trading/live_trading.html` [UPDATED] — Added style.css import

### Tests
- ✅ Menu replié n'occulte plus le contenu (desktop)
- ✅ Pas de flicker au rechargement (localStorage)
- ✅ Pas d'ouverture du menu après clique sur tabs
- ✅ Pas de flicker lors de changement de page
- ✅ CSS chargé correctement sur toutes les pages
- ✅ Layout responsive testé visuellelement (tableau + mobile)

### Known limitations
- Portfolio chart pas testé sur très petits écrans (< 300px)
- Menu mobile peut pas scrollable si 20+ items (UX à améliorer)

---

## 2026-09-11 | UI POLISH + PWA | Chart design, menu fonts, eye toggles, PWA fondations

### Chart Dashboard
- Fond transparent au lieu de blanc
- Removed grid lines
- Removed axis borders
- Buttons TF/catégorie restylés (pilule design)

### Menu
- Font-size 13px → 16px
- Font-weight 600 → 700

### Eye Toggle (Password)
- login.html : toggle password visibility
- Material Icons link ajouté au head

### Eye Toggle (KPI)
- kpi-cards.html : `.kpi-toolbar` avec bouton toggle
- localStorage `kpiHidden:<pathname>` pour persistance par page
- CSS `.kpi-hidden .kpi-value { filter: blur(7px) }`

### PWA Foundations
- `apps/dashboard/views.py` : routes `manifest()` + `service_worker()`
- `static/js/service-worker.js` : runtime caching
- `static/js/pwa-register.js` : conditional registration
- Toutes les pages : `<link rel="manifest">`, `<meta name="theme-color">`, `<link rel="apple-touch-icon">`
- Icône unique `static/icons/icon.svg` (à générer PNG 192×512 pour installabilité complète)

---

## 2026-09-10 | AUDIT PRODUCTION | P0/P1 fixes, heartbeat BDD, HTTPS guard

### P0 Blocages
1. **Ordre exécuté avant persistance** → KrakenOrderAttempt journal + userref Kraken
2. **Retry Kraken + nonce** → KrakenNonceCounter compteur DB (select_for_update)
3. **Double clôture concurrence** → is_closing boolean + atomic filter/update

### P1 Rapides
- Watcher heartbeat : fichier → BDD (WatcherHeartbeat singleton)
- Isolation watcher : try/except par position
- Clé API unique par plateforme (ApiCredentialForm.clean())
- HTTPS obligatoire (RuntimeError si DEBUG=False sans sécurité SSL)

### Tests
- 19 tests : reconciliation + concurrence
- Tous verts ✅

### Déploiement
- Render web + Railway worker + Neon DB
- Whitenoise pour statiques en prod
- Auto-détection Render ALLOWED_HOSTS

---

## 2026-09-09 | LIVE TRADING + CLÉS API | Filtres mode, validation IRC, ApiCredential chiffré

### Live Trading
- Page `/live/` : ouverture spot/futures + suivi JSON
- Validation IRC 4h (regime, SAR, volume profile) pour LIVE
- Watcher TP/SL intégré

### Trade Mode
- Tabs LIVE/PAPER/ALL sur spot_trading + futures_trading
- Query param `?mode=LIVE|PAPER|ALL`
- Badges `.investment-action-live` / `.investment-action-paper`

### ApiCredential
- Modèle : platform/label/api_key/api_secret/passphrase chiffrés
- Fernet symétrique (Fernet, clé SHA256 de SECRET_KEY)
- CRUD : create/delete uniquement
- Admin : read-only

---

## 2026-09-08 | ANALYTICS + JOURNAL + TRADE MODE | Stats futures, nouveaux modèles

### Pages
- `apps/analytics` : Win rate, Profit factor, R moyen, ventilations
- `apps/journal` : Liste chronologique trades avec PnL dynamique

### Modèles
- FuturesTrading.trade_mode (PAPER/LIVE, default PAPER)
- Migration 0006

### Stats
- `compute_futures_analytics(trade_mode)` : positions clôturées seulement
- `futures_trade_pnl(trade)` : réalisé d'une position

---

## 2026-09-07 | INVESTMENT REFACTOR + STRATEGY | Models entry_date, Portfolio stats

### Models
- Investment.entry_date : `default=timezone.now` (pas auto_now_add)
- FuturesTrading.strategy : CharField for Notion journal
- Migration 0005

### Portfolio Service
- `compute_investment_stats()`, `compute_spot_stats()`, `compute_futures_stats()`
- `compute_global_stats()` : agrégation uniquement
- `build_chart_series()` : séries cumulées par catégorie

### Dashboard
- KPI cards globales seulement (Portfolio Value, Capital, PnL Global)
- Chart cost basis (pas mark-to-market)

---

## 2026-09-06 | KRAKEN IMPORT | TradesHistory sync, external_ref idempotence

### Portfolio Service
- `sync_kraken_trades()` : import idempotent via external_ref (txid Kraken)
- Utilisé par Investment page + import_kraken_trades command

### Models
- Investment.external_ref : CharField for Kraken txid
- Migration 0004

---

## 2026-09-01 à 2026-09-05 | FOUNDATION RELEASE | Django setup, models, core features

### Initial setup
- Django 5.2 + Python 3.11
- 8 apps : core, dashboard, investment, spot_trading, futures_trading, analytics, journal, live_trading
- DeFi dark theme CSS

### Models
- Investment (abstract) + SpotTrading/FuturesTrading
- SimpleInvestment (legacy CSV)
- Kraken client + price fetching

### Pages
- Dashboard : KPI + portfolio chart
- Investment, Spot, Futures, Analytics, Journal, Live
- Settings : API credentials

### Tests
- Core models, views, services
- All green ✅
