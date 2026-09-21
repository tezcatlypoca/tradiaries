# Tradiaries — Change Log

**Format** : ISO 8601 YYYY-MM-DD | Catégorie | Description courte | Fichiers modifiés  
**Dernière entrée** : 2026-09-21

---

## 2026-09-21 | FEATURE | Refonte UI page Trading : dropdown actifs, graphique volume/SAR, drag & drop TP/SL

### Améliorations UX
1. **Sélection d'actifs** : remplacé la liste de boutons par un dropdown placé dans la toolbar du graphique
   - Moins encombrant, meilleur responsive
   - Conserve tous les symboles par défaut

2. **Hauteur et largeur du graphique** :
   - Augmentation hauteur graphique : 420px → 480px
   - Le graphique comble désormais la largeur entière (grid 2 colonnes au lieu de 3)
   - Deux graphiques : OHLC (480px) + Volume (120px)

3. **Indicateurs techniques** :
   - Ajout graphique de **volume** (histogramme coloré : vert si haussier, rouge si baissier)
   - Ajout **SAR (Stop And Reverse)** : courbe pointillée jaune, calculé via algorithme Wilder
   - Synchronisation timeScale entre les deux graphiques

4. **Drag & drop TP/SL** :
   - Correction bug : utilisation cohérente de priceScale.coordinateToPrice()
   - Augmentation seuil détection : 8px → 12px (plus facile de cliquer)
   - Validations : prix > 0 pour éviter erreurs NaN

**Fichiers modifiés** :
`apps/live_trading/templates/live_trading/live_trading.html`, `static/css/trading.css`, `apps/live_trading/tests.py`

**Tests** : 42 tests passants (1 test updated : cherche maintenant `id="assetSelect"` au lieu de `trading-asset-btn`)

---

## 2026-09-21 | CLEANUP | Consolidation import dupliqué (audit)

### Correction d'audit
- Import dupliqué de `healthz` dans `config/urls.py` (lignes 22-23) consolidé en une seule ligne.
- Aucun impact fonctionnel (nettoyage de lisibilité du code).
- Tests : 42 tests passants ✓

**Fichiers modifiés** : `config/urls.py`

---

## 2026-09-21 | FEATURE | Page Positions unifiée + refonte exchange-like de la page Trading

> Note process : cette implémentation a été menée sans passer par les étapes Challenge / Gel des
> décisions / Planification, sur override explicite de l'utilisateur (le Dégrossissage avait déjà
> abouti à une proposition suffisamment précise). Aucune entrée n'a donc été ajoutée à
> `decisions.md` ; ce paragraphe fait office de trace de ce qui a réellement été construit.

### Idée 1 — Fusion Spot / Futures dans une page "Positions"
- Nouvelle app `apps/positions` (lecture seule) : onglets Spot / Futures (Investissements simples
  volontairement exclus, conserve sa propre page), filtre par mode, KPI recalculées côté serveur via
  les fonctions existantes `compute_spot_stats` / `compute_futures_stats`.
- Pas de création ni de clôture de position depuis cette page (conforme à la demande) ; l'édition est
  remplacée par un panneau de détail en lecture seule (`static/js/positions-detail-panel.js`). La
  suppression reste déléguée aux vues `spot_trading:delete` / `futures_trading:delete` existantes.
- **Choix assumé** : les anciennes pages `spot_trading` et `futures_trading` ne sont pas supprimées ni
  redirigées, seulement retirées du menu, pour limiter le risque de régression sur leurs tests/usages
  restants.
- Menu (`components/side-menu.html`) : les liens "Trading Spot" / "Trading Futures" sont remplacés par
  un unique lien "📂 Positions".
- Tests : `apps/positions/tests.py` (6 tests, isolation multi-utilisateur, filtres, KPI).

### Idée 2 — Page "Trading" refondue en interface exchange-like
- `apps/live_trading/templates/live_trading/live_trading.html` réécrite : liste d'actifs, graphique en
  chandeliers (Lightweight Charts) et ticket d'ordre avec bascules Spot/Futures, Paper/Live, Long/Short,
  et lignes de prix Entrée/TP/SL déplaçables directement sur le graphique (glissé-déposé), synchronisées
  avec les champs du formulaire. La checklist IRC de validation des ordres LIVE est conservée à
  l'identique (2 confirmations sur 3 requises), de même que le rejet des ordres futures en LIVE.
- Backend : `apps/core/kraken_client.py::fetch_ohlc()` (nouvel appel public Kraken OHLC, caché 30s,
  retombe sur `[]` si Kraken est indisponible) ; nouvelle route `apps/live_trading/urls.py` →
  `ohlc.json` servie par `apps/live_trading/views.py::ohlc_json`. Les vues `open_position`,
  `close_position`, `positions_json` sont inchangées.
- **Nouvelle dépendance structurante (signalée)** : librairie *Lightweight Charts* v4.1.3 (TradingView,
  licence Apache-2.0), auto-hébergée dans `static/js/vendor/lightweight-charts.standalone.production.js`
  plutôt que chargée depuis un CDN, pour rester cohérent avec le déploiement Whitenoise du projet.
- **Hors périmètre** : l'idée 3 (script de dimensionnement automatique de position) a été explicitement
  exclue par l'utilisateur ("trop d'info... je n'utilise jamais 'trading live'") et n'a pas été
  implémentée.
- **Non couvert par les tests automatisés** : le glissé-déposé des lignes de prix sur le canvas du
  graphique nécessite une vérification manuelle en navigateur (non testable unitairement).
- Tests : `apps/core/tests.py::KrakenOhlcTests` (3 tests), `apps/live_trading/tests.py::OhlcJsonViewTests`
  et `TradingPageRenderingTests` (3 tests). Suite complète du projet : 42 tests, OK.

### Fichiers modifiés/créés
`apps/positions/**` (nouveau), `static/js/positions-detail-panel.js` (nouveau), `static/css/investment.css`,
`static/css/trading.css` (nouveau), `static/js/vendor/lightweight-charts.standalone.production.js` (nouveau),
`apps/core/kraken_client.py`, `apps/core/tests.py`, `apps/live_trading/views.py`, `apps/live_trading/urls.py`,
`apps/live_trading/templates/live_trading/live_trading.html`, `apps/live_trading/tests.py`,
`config/settings.py`, `config/urls.py`, `components/side-menu.html`.

---

## 2026-09-18 | FEATURE | Time frame visible, stratégie utilisateur, Coaching et scrollbars

### Interface et données
- Les listes Spot et Futures affichent maintenant le champ `timeframe` déjà présent en base et dans
  leurs formulaires.
- Nouveau modèle `UserPreferences`, lié en OneToOne au compte, avec un champ `strategy` en texte long.
  La page Paramètres permet à chaque utilisateur d'enregistrer et de modifier sa propre stratégie.
- Migration `core.0016_userpreferences` ajoutée ; elle devra être appliquée en production lors du
  prochain déploiement, sans modification des données existantes.

### Navigation et thème
- Nouvelle route authentifiée `/coaching/`, ajoutée au menu ; son contenu reste volontairement vide.
- Les scrollbars utilisent désormais le fond global sombre et le vert primaire des boutons, sur Firefox
  comme sur les navigateurs WebKit.

### Tests
- Couverture d'intégration ajoutée pour la persistance et l'affichage du `timeframe`, la sauvegarde et
  l'isolation de la stratégie utilisateur, ainsi que l'accès à la page Coaching vide.

---

## 2026-09-18 | DEBUG | 500 déploiement Render vs local

### Diagnostic
- Reproduction locale en configuration proche production (`DEBUG=False`) : les routes de base répondent
  sans 500 en HTTPS simulé (`/` → 302, `/accounts/login/` → 200, `/healthz/` → 200,
  `/service-worker.js` → 200, `/manifest.webmanifest` → 200). `collectstatic` passe aussi avec
  `CompressedManifestStaticFilesStorage`.
- Cause probable si Render affiche directement une erreur serveur au démarrage : variable
  `API_CREDENTIAL_ENCRYPTION_KEY` absente ou invalide. `config/settings.py` lève explicitement
  `RuntimeError: API_CREDENTIAL_ENCRYPTION_KEY must be configured when DEBUG=False`, ce qui est
  cohérent avec un commit qui fonctionne localement (`DEBUG=True`) mais tombe en prod (`DEBUG=False`).
- Autre point à vérifier côté Render/Neon si le 500 apparaît seulement sur les pages de trading :
  migration `core.0015_futurestrading_timeframe_spottrading_timeframe` bien appliquée sur la base
  production (`python manage.py migrate --check`).

### Correctif préventif
- `.github/workflows/django.yml` : ajout de `API_CREDENTIAL_ENCRYPTION_KEY` au `check --deploy` CI et
  exécution de `collectstatic` avec `DEBUG=False` + variables de sécurité production. Le workflow
  détectera désormais plus tôt une configuration prod cassée au lieu de tester `collectstatic` en mode dev.

### Action Render attendue
- Définir `API_CREDENTIAL_ENCRYPTION_KEY` dans les variables d'environnement Render avec une vraie clé
  Fernet générée par `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Vérifier que le Build Command Render reste :
  `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`.

---

## 2026-09-14 | FEATURE | Champ `timeframe` sur le modèle mère Investment

### Contexte
Ajout d'une donnée "Time frame" (ex: 15min, 1h, 4h, 1D) sur les positions de trading, à la demande
de l'utilisateur. Clarifié avec lui : texte libre (comme `strategy`), optionnel — pas de liste fixe.

### Modèles + migration
- `apps/core/models.py` : nouveau champ `Investment.timeframe` (`CharField(max_length=20, blank=True)`)
  sur le modèle abstrait mère — hérité par `SpotTrading` et `FuturesTrading` (pas `SimpleInvestment`,
  qui n'hérite pas de `Investment`).
- Migration `core.0015_futurestrading_timeframe_spottrading_timeframe` (AddField sur les deux tables
  concrètes, colonne nullable via `blank=True`, aucune perte de données). Appliquée en local
  (`python manage.py migrate core`). Suite de tests ciblée verte (23 tests : `apps.core`,
  `apps.spot_trading`, `apps.futures_trading`).

### Formulaires + templates
- `apps/core/forms.py` : `TradingForm.Meta.fields` inclut désormais `timeframe` (hérité par
  `SpotTradingForm` et `FuturesTradingForm`).
- `components/spot-trading-form.html`, `components/futures-trading-form.html` : nouveau champ texte
  `timeframe` dans le modal de création/édition + population dans `openEditTradeModal()`.
- `apps/spot_trading/templates/spot_trading/spot_trading.html`,
  `apps/futures_trading/templates/futures_trading/futures_trading.html` : `data-timeframe` ajouté au
  bouton d'édition (pas de nouvelle colonne dans le tableau, même traitement que `strategy` qui n'est
  pas encore affiché en colonne — voir "à faire" dans project-context.md).

### Production (Neon via Render)
- Non appliqué par l'IA (règle d'autonomie : migration de schéma sur une base de production =
  validation obligatoire). Le Build Command Render (`deploy/README.md`) exécute déjà
  `python manage.py migrate` à chaque déploiement — un simple `git push` suffit donc à propager cette
  migration en prod au prochain déploiement. Marche à suivre détaillée transmise à l'utilisateur en fin
  de session.

### Contexte
En vue d'un futur module de coaching IA, l'app devait d'abord gérer correctement plusieurs comptes.
Audit du code (voir `docs/audit-production.md`, section "Autorisation globale") confirmé : `login_required`
protégeait les vues, mais aucun modèle n'avait de propriétaire — n'importe quel compte connecté pouvait
voir/modifier/supprimer les trades et clés API de n'importe quel autre compte (IDOR). Décision validée
avec l'utilisateur (voir `decisions.md`) : isolation complète des données + page d'inscription publique.

### Modèles (apps/core/models.py) + migrations 0012/0013/0014
- Ajout d'un champ `user` (FK vers `AUTH_USER_MODEL`, `on_delete=CASCADE`) sur `Investment` (abstrait, donc
  `SpotTrading`/`FuturesTrading`), `SimpleInvestment`, `ApiCredential`, `KrakenOrderAttempt`.
- `KrakenNonceCounter` passe de singleton global (pk=1) à un compteur `OneToOneField(user)` : chaque compte
  a son propre espace de nonce Kraken (spécifique à une paire clé/secret).
- Migration en 3 temps : `0012` ajoute les champs nullable, `0013` (data migration) rattache tout l'historique
  au superuser existant (`samsan`), `0014` rend les champs obligatoires. `WatcherHeartbeat` reste un singleton
  global (heartbeat du process watcher lui-même, pas une donnée utilisateur).

### Services (portfolio_service.py, trading_service.py, kraken_client.py)
- Toutes les fonctions de stats/agrégation prennent désormais un paramètre `user` obligatoire et filtrent
  leurs querysets en conséquence : `compute_investment_stats`, `compute_spot_stats`, `compute_futures_stats`,
  `compute_global_stats`, `compute_futures_analytics`, `build_chart_series`, `sync_kraken_trades`.
- `trading_service.open_position(user=...)` et `live_positions(user)` scopent la création/lecture des
  positions ; `close_position`/`check_tp_sl` utilisent `trade.user` pour retrouver les bonnes clés Kraken
  (le watcher continue d'itérer sur TOUTES les positions ouvertes, tous utilisateurs confondus, mais chaque
  clôture LIVE utilise les clés Kraken propres au propriétaire de la position — pas de clé globale partagée).
- `kraken_client.py` : `_get_kraken_credentials`, `_next_nonce`, `_private_request`, `add_spot_order`,
  `query_orders`, `fetch_order_fill_price`, `cancel_order`, `fetch_trades_history` prennent tous un `user`.
  Les endpoints publics (`fetch_current_price(s)`, `resolve_pair`) restent globaux (marché partagé, pas
  de secret impliqué).
- `ApiCredentialForm` (apps/core/forms.py) prend un `user` en `__init__` : l'unicité "une clé par
  plateforme" est désormais vérifiée par utilisateur (et non plus globalement).

### Vues (dashboard, investment, spot_trading, futures_trading, analytics, journal, live_trading)
- Tous les querysets de liste filtrent sur `request.user`. Toute création assigne explicitement
  `obj.user = request.user` avant sauvegarde. Tous les `get_object_or_404(...)` d'update/delete/close
  ajoutent `user=request.user` — corrige la faille IDOR (404 au lieu d'un accès/modif croisé).

### Inscription (nouveau)
- Vue `apps/dashboard/views.signup` (formulaire `apps/dashboard/forms.SignupForm`, basé sur
  `UserCreationForm`) : connexion automatique après inscription, compte créé sans aucune donnée
  préexistante. Route `accounts/signup/` (avant l'include `django.contrib.auth.urls`).
- Template `apps/dashboard/templates/registration/signup.html` (même style que `login.html`,
  `static/css/auth.css`). Lien croisé ajouté entre `login.html` et `signup.html`.

### Commande de management
- `import_kraken_trades` exige désormais `--username <compte>` (les clés Kraken et les investissements
  importés sont propres à un utilisateur, plus de comportement implicite global).

### Tests
- `apps/core/tests.py` : tests existants adaptés (ajout de `user=` sur les appels directs à
  `open_position`/`SpotTrading.objects.create`). Nouvelle classe `MultiUserIsolationTests` (5 tests) :
  un utilisateur ne voit que ses propres trades, ne peut pas modifier/supprimer les données d'un autre
  (404), et toute création est bien rattachée à l'utilisateur authentifié.
- Suite complète : 26 tests, tous verts. `python manage.py check` : OK.

### Non traité dans cette passe (décisions en suspens, voir decisions.md)
- Clé de chiffrement Fernet (`apps/core/crypto.py`) reste globale (dérivée de `SECRET_KEY`), pas
  encore par utilisateur — hors périmètre de cette session (isolation des données ≠ dérivation de clé).
- Rate limiting / quotas Kraken par utilisateur : non traité (roadmap `docs/tradiaries-plan-prod.md`).
- Le module de coaching IA lui-même n'a volontairement pas été développé (hors périmètre demandé).

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
