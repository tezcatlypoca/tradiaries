# Tradiaries — Change Log

**Format** : ISO 8601 YYYY-MM-DD | Catégorie | Description courte | Fichiers modifiés  
**Dernière entrée** : 2026-09-27

---

## 2026-09-27 | FEATURE | Bandeau Vigil : tags + titre sur les cards, vue détaillée cliquable avec scores

### Décision implémentée
Suite à une demande directe de l'utilisateur (implémentation directe, sans repasser par Challenge/Gel/Planification — même précédent que le 2026-09-21). Confirmé avec l'utilisateur avant implémentation (voir questions posées en session) : exposer `impact_score`/`news_score` dans la vue détaillée (révision assumée de la décision du 2026-09-25, documentée dans `decisions.md`), et traiter `summary` à la fois comme titre (tronqué visuellement par le CSS de la card) et comme corps complet (pas de champ distinct côté API Vigil).

### Implémentation
- `apps/live_trading/views.py::vigil_signals_json` : ajout de `impact_score`/`news_score` au JSON exposé (toujours **pas** de `raw_payload`).
- `apps/live_trading/templates/live_trading/live_trading.html` :
  - Card Vigil : nouveau tag dérivé de `source` (`VIGIL_SOURCE_TAGS` — ex. `onchain_ethereum` → "On-chain", `news_editorial`/`news_aggregator` → "Éditorial") affiché au-dessus du badge de fiabilité existant. Card transformée en `<button>` cliquable (accessible clavier).
  - Nouvelle `<dialog id="vigilSignalDialog">` (natif HTML, `showModal()`) : résumé complet, tag, fiabilité, ticker + date formatée, et un bloc scores dans un `<details>` replié par défaut ("Voir les scores détaillés" — spoiler, cohérent avec le principe d'affichage neutre : les scores restent une consultation volontaire). Fermeture par `✕`, clic sur le fond, ou touche Échap (comportement natif `<dialog>`).
  - Scores affichés : `impact_score`, `news_score.novelty`, `news_score.source_count`, `news_score.importance` (par bucket intraday/swing/position) — absents proprement (message dédié) si le signal n'a aucun score.
- `static/css/trading.css` : styles `.vigil-signal-tag`, `.vigil-signal-dialog*`, `.vigil-signal-score*` (thème sombre cohérent avec le reste de la page Trading).

### Tests
- `apps/live_trading/tests.py::VigilSignalsJsonViewTests::test_exposes_scores_but_never_raw_payload` (nouveau) : vérifie `news_score`/`impact_score` transmis, `raw_payload` toujours absent.
- Suite complète : 96 tests, tous verts (`python manage.py test apps.live_trading apps.core apps.dashboard apps.positions`).

### Vérification manuelle
Serveur de dev + compte de test temporaire (`vigil_manual_check2`, supprimé après coup) via Claude in Chrome : 4 cards mockées injectées en JS (tags Éditorial/Flux ETF/On-chain visibles, un signal macro `ticker=null` sans tag actif rendu correctement), clic sur une card ouvre le dialog avec résumé complet + métadonnées, ouverture du spoiler affiche les 6 lignes de score attendues (Impact, Nouveauté, Sources corroborantes, Importance ×3), signal sans score affiche "Aucun score disponible pour ce signal." Aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/views.py`, `apps/live_trading/templates/live_trading/live_trading.html`, `static/css/trading.css`, `apps/live_trading/tests.py`, `.ai/decisions.md`.

---

## 2026-09-27 | FIX/DOC | Bandeau Vigil invisible en local — VIGIL_API_URL sans préfixe /api

### Constat
Session de reprise sur l'intégration Vigil (état vérifié cohérent, aucune contradiction code/doc). L'utilisateur a signalé le bandeau de news vide sur la page Trading en local, malgré une instance Vigil locale fonctionnelle (confirmée via son interface de monitoring et `curl http://localhost:8100/api/health`).

### Cause
`.env` local avait `VIGIL_API_URL="http://localhost:8100/"` (sans `/api`). `apps/core/vigil_client.py::fetch_signals()` construit l'URL comme `{VIGIL_API_URL}/signals` — le préfixe `/api` doit donc déjà être inclus dans `VIGIL_API_URL` (cohérent avec l'exemple de client officiel dans `docs/API_DOCUMENTATION.md`). Résultat : 404 côté Vigil, avalé silencieusement par `except requests.RequestException` → `fetch_signals()` retourne `[]` sans erreur visible, bandeau resté masqué (comportement de dégradation gracieuse fonctionnant comme prévu, mais masquant la vraie cause).

### Correctif
- `.env` local corrigé : `VIGIL_API_URL="http://localhost:8100/api"` (non commité, fichier gitignored).
- `.env.example` : ajout des variables `VIGIL_API_URL`/`VIGIL_BEARER_TOKEN`/`VIGIL_TIMEOUT_SECONDS` (absentes jusqu'ici, alors que documentées comme requises dans `project-context.md`), avec commentaire explicite sur le préfixe `/api` obligatoire et sur le bearer optionnel en dev si l'auth est désactivée côté Vigil.

### Fichiers modifiés
- `.env.example`

---

## 2026-09-25 | FEATURE | Refonte responsive tablette + smartphone (en cours)

### Décision implémentée
Suite à `/planification` (2026-09-25, vérifié visuellement via Claude in Chrome — voir `docs/plan-responsive-tablette-2026-09-25.md` et `docs/plan-responsive-smartphone-2026-09-25.md`) : implémentation des missions des deux plans, dans l'ordre de priorité.

### Unification des breakpoints (M1 tablette)
`static/css/style.css` : seuils unifiés sur `≤599px` (mobile) / `600–1024px` (tablette) / `>1024px` (desktop), remplaçant les 3 systèmes divergents (768/769 dans `style.css`, 599/600 dans `investment.css`, 1024 seul dans `trading.css`).

### Menu latéral : calque à 3 états au lieu de 2 (M2 tablette, M1 smartphone)
- **Bug corrigé (M1 smartphone)** : sur mobile, `.main-content` recevait `margin-left: 64px` même quand le menu était fermé (`.side-menu.hidden`), alors que le menu est censé être entièrement hors-écran — 17% de la largeur d'écran perdue en permanence. Le menu est désormais un calque superposé (même cellule de grille que `.main-content`, jamais de push) sur toute la plage `≤1024px` : `.main-content` ne reçoit plus jamais de `margin-left` réservée.
- **Nouveau comportement tablette (M2)** : rail à icônes replié par défaut (64px de large réel, pas un calque tronqué d'une sidebar pleine largeur — première tentative ratée : centrer le contenu dans une sidebar de 240px décalée en `transform` place le contenu centré hors du champ visible de 64px ; corrigé en rétrécissant réellement la largeur du menu à 64px sur cette plage). Icônes des liens + icône de marque "T" séparées du texte via `<span class="menu-icon">`/`<span class="menu-label">` (`components/side-menu.html`) pour pouvoir masquer le texte (`display:none`, pas seulement `opacity:0` — un label invisible mais toujours dans le flux flex décentre l'icône) tout en gardant l'icône visible.
- Clic sur le rail/header bascule désormais dans les deux sens (`toggleMenu()`), pas seulement fermeture — nécessaire car le header reste visible en permanence sur tablette (contrairement au mobile où il est hors-écran).
- Bouton hamburger flottant (`.menu-toggle`) masqué à partir de 600px (redondant avec le rail toujours visible et cliquable).
- **Bug préexistant découvert et corrigé au passage** : l'overlay semi-transparent affiché quand le menu mobile est ouvert ne s'affichait jamais — la règle de base définissait `body::before` mais la règle d'activation ciblait `.main-content::before` (deux pseudo-éléments différents, celui réellement stylé n'était jamais activé). Fusionné en une seule paire de règles cohérente sur `.main-content::before`.
- `isMobile` (seuil 768px) renommé `isCompact` (seuil 1024px) dans `components/side-menu.html` : mobile ET tablette démarrent repliés par défaut (au premier chargement, sans état `localStorage` préexistant) ; seul le desktop reste ouvert.

### Bug d'environnement découvert en cours de route (sans lien avec le code applicatif)
Le processus `runserver` lancé en tout début de session servait des templates/CSS périmés malgré des édits ultérieurs sur disque (confirmé : un process Django frais relit le fichier à jour immédiatement) — cause exacte non identifiée, corrigé en redémarrant le process. Un service worker PWA actif (`tradiaries-cache-v1`) et le cache HTTP normal du navigateur ont également servi du CSS périmé dans le harnais de vérification visuelle (iframe same-origin, voir session `/planification`) malgré `cache: 'no-store'` sur les `fetch()` explicites — les `<link>` de l'iframe, eux, suivent le cache HTTP standard. Corrigé en désenregistrant le service worker, vidant les caches, et ajoutant un paramètre `?_cb=<timestamp>` aux URLs `/static/...` dans le harnais de test.

### Vérification manuelle (via harnais iframe same-origin, voir note méthodologique dans les plans)
- Tablette (900×1024) : rail 64px avec icônes visibles confirmé par capture, clic sur le rail ouvre le drawer complet (240px) avec overlay assombri sur le contenu, reclic referme.
- Mobile (390×844) : `margin-left` confirmé à `0px` (`mainContentClientWidth` passé de 316px à 380px sur 390px de large), drawer plein écran fonctionnel avec overlay, bouton hamburger visible.

### Page Trading : seuil colonne unique abaissé + hauteurs de graphique adaptatives (M4 tablette + smartphone)
- `static/css/trading.css` : seuil de bascule `.trading-workspace` (chart | ticket → empilé) abaissé de `1024px` à `767px` — propre à ce composant (un ticket fixe de 320px ne laisse plus assez de large pour un graphique lisible en-dessous de ~768px), pas aligné sur les seuils globaux 600/1024 de M1. `.trading-chart-toolbar` passe en `flex-wrap` sous 599px (symbole sur sa propre ligne via `order:-1`).
- `apps/live_trading/templates/live_trading/live_trading.html` : hauteurs de graphique (`computeChartHeights()`) désormais fonction de `window.innerWidth` (240/70 ≤599px, 320/90 ≤767px, 480/120 au-delà) au lieu de valeurs JS fixes ; réappliquées automatiquement via le `ResizeObserver` déjà en place (pas de nouveau listener).
- **Vérifié à 1024×768** (tablette paysage, cas mesuré comme problématique en Planification) : workspace repasse en 2 colonnes (534px + 320px), hauteur totale de contenu réduite de 1938px à 1221px, bouton de soumission à 854px du haut au lieu de 1567px.
- **Vérifié à 390×844** : toolbar ne déborde plus (`containerScrollWidth === containerClientWidth`, confirmé par capture — les 4 boutons d'intervalle tiennent sur leur propre ligne).

### Tableaux larges : colonnes secondaires masquées sur tablette + panneau de détail généralisé (M3 tablette, M2 smartphone)
- **`data-label` ajoutés** (mobile, conversion carte) sur les 3 pages qui en manquaient : `apps/investment/templates/investment/investment.html`, `apps/positions/templates/positions/positions.html`, `apps/live_trading/templates/live_trading/live_trading.html` (template **et** fonction JS `renderRow()`, pour rester synchronisé après chaque cycle de polling).
- **Nouvelle classe utilitaire `.col-tablet-hide`** (`static/css/investment.css`) : masque une colonne sur la plage 600-1024px quand sa donnée reste accessible via le panneau de détail. Appliquée aux colonnes Exchange/Mode (Positions) et TP/SL (Trading — positions ouvertes).
- **Panneau de détail généralisé** : `static/js/positions-detail-panel.js` renommé `static/js/row-detail-panel.js`, sélecteur `.position-row` renommé `.detail-row` (CSS + template Positions), `FIELD_LABELS` complété (`price`, `action`, `currentPrice`, `pnl`) pour couvrir les nouveaux consommateurs. Réutilisé tel quel sur la page Trading (positions ouvertes, nouveau panneau — n'existait pas avant) ; `window.wireDetailRow` exposé pour re-câbler les lignes régénérées par le polling. Page Investissements : `data-label` ajouté mais **pas** de nouveau panneau de détail (redondant avec la modale d'édition déjà existante) ni de colonne masquée (6 colonnes seulement, aucun débordement mesuré à 900px après le fix du rail de menu).
- **Vérifié à 900×1024** (Positions) : `.main-content` scrollWidth === clientWidth (890px, contre 851px/650px avant, débordement complètement résorbé), capture d'écran confirmant `Exchange`/`Mode` masqués. Panneau de détail testé au clic sur Positions et sur Trading (mobile 390px) : fonctionnel dans les deux cas.
- **Débordement résiduel mineur constaté** (non corrigé) : le tableau des positions ouvertes de Trading déborde encore de ~23px à 900px même après masquage TP/SL (9 colonnes visibles restantes) — largement inférieur au débordement initial (161px) mais pas totalement nul. À revisiter si signalé comme gênant en usage réel.

### Barre de navigation basse mobile (M3 smartphone, nouveau composant)
- `components/bottom-tab-bar.html` (nouveau) + `static/css/bottom-tab-bar.css` (nouveau) : 5 entrées (Dashboard/Positions/Trading/Journal/Menu — sélection confirmée avec l'utilisateur avant implémentation), visible uniquement `≤599px`, état actif calculé côté client (`window.location.pathname`). Le 5e item délègue au `menuHeader` existant pour ouvrir le drawer complet (Analytics/Investissements/Coaching/Paramètres).
- Bouton hamburger flottant (`.menu-toggle`) masqué sur mobile (redondant avec l'item "Menu") ; tab bar elle-même masquée pendant que le drawer complet est ouvert.
- `.main-content` : `padding-bottom` étendu sur mobile pour ne jamais faire chevaucher le contenu (notamment le bouton de soumission du ticket Trading).
- Inclus dans les 8 templates qui chargent `components/side-menu.html` (`dashboard.html` — hérité par `settings.html` via `extends` —, `investment.html`, `positions.html`, `spot_trading.html`, `futures_trading.html`, `journal.html`, `analytics.html`, `live_trading.html`).

### Bouton de soumission collant sur la page Trading (M6 smartphone, nouveau — confirmé nécessaire par la mesure M4)
`static/css/trading.css` : `.trading-submit` en `position: sticky` (borné à `.trading-ticket`, donc actif seulement tant que le ticket est à l'écran) sur mobile et tablette-colonne-unique (≤767px), avec dégagement pour la bottom-tab-bar mobile. Contrairement au sélecteur d'actif plein écran (également proposé en option dans le plan), pas construit : aucun besoin confirmé, resterait de la sur-ingénierie.

### `credential-item` (Paramètres) : wrap sur tablette (M5 tablette)
`static/css/investment.css` : `flex-wrap` sur `.credential-item` et `.credential-info` pour éviter un débordement avec une clé API longue + libellé sur largeur réduite.

### Découvertes hors périmètre des deux plans (non corrigées, signalées)
- 🟡 `apps/spot_trading/templates/spot_trading/spot_trading.html` et `apps/futures_trading/templates/futures_trading/futures_trading.html` débordent encore à 900px (~90-96px) — ces deux pages ne sont **plus liées depuis le menu** (remplacées par la page Positions unifiée du 2026-09-21) et n'étaient pas couvertes par le diagnostic initial. Laissées telles quelles : corriger nécessiterait de ré-auditer des pages orphelines hors du parcours utilisateur réel.
- 🟡 Bug d'environnement local persistant : le processus `runserver` a servi du contenu de template périmé à plusieurs reprises pendant cette session malgré `DEBUG=True` et des fichiers à jour sur disque (confirmé via un process `manage.py shell` séparé à chaque fois) — cause exacte non identifiée (pas de cache middleware, pas de `cached.Loader` configuré). Mitigé en redémarrant le process avant chaque vérification critique ; à surveiller si ça persiste lors de la prochaine session de dev.

### Suite de tests
`python manage.py test apps.core apps.live_trading apps.dashboard apps.positions` : 95 tests, tous verts après l'ensemble des changements ci-dessus (aucun test de rendu cassé par les changements de markup).

### Vérification manuelle finale (harnais iframe same-origin, toutes les pages)
Passe automatisée sur les 9 routes principales × 2 largeurs (390/900px) : 0px de débordement partout sauf les 2 pages orphelines signalées ci-dessus. Zone grise 768px re-testée : sidebar 240px + KPI 2 colonnes + tab bar masquée, comportement tablette correct (contre mode mobile par erreur avant M1).

### À faire (hors périmètre de ce chantier, ou dépendant d'un test sur appareil réel)
- M5 smartphone (vérification paysage téléphone 600-900px) : non testée dans le harnais iframe cette session, à faire sur appareil réel ou émulateur.
- Geste tactile pour déplacer TP/SL sur le graphique Trading (point en suspens signalé dans le plan smartphone, décision produit à trancher séparément).
- Vérification sur appareil physique/Chrome DevTools classique recommandée avant prod (le harnais iframe reproduit fidèlement les media queries CSS mais pas le clavier virtuel, la barre d'adresse rétractable, ni les gestes tactiles natifs).

**Fichiers modifiés/créés** : `static/css/style.css`, `static/css/side-menu.css`, `components/side-menu.html`, `static/css/trading.css`, `apps/live_trading/templates/live_trading/live_trading.html`, `static/js/row-detail-panel.js` (nouveau, remplace `static/js/positions-detail-panel.js` supprimé), `static/css/investment.css`, `apps/positions/templates/positions/positions.html`, `apps/investment/templates/investment/investment.html`, `components/bottom-tab-bar.html` (nouveau), `static/css/bottom-tab-bar.css` (nouveau), `apps/dashboard/templates/dashboard/dashboard.html`, `apps/spot_trading/templates/spot_trading/spot_trading.html`, `apps/futures_trading/templates/futures_trading/futures_trading.html`, `apps/journal/templates/journal/journal.html`, `apps/analytics/templates/analytics/analytics.html`.

---

## 2026-09-25 | FEATURE | Bandeau de news Vigil sur la page Trading

### Décision implémentée
Suite au Challenge + `/gel-decision` du 2026-09-25 (`.ai/decisions.md` → "Intégration des news Vigil — Bandeau contextuel sur la page Trading") et au plan `docs/plan-integration-vigil-2026-09-25.md` : bandeau de cards à défilement horizontal manuel sur la page Trading, filtré par une liste d'actifs suivis déclarée dans Paramètres + signaux macro/géopolitiques toujours affichés.

### Découverte en vérifiant le code (corrige une hypothèse du Challenge)
Le mapping supposé nécessaire entre `symbol` Tradiaries (paire exchange) et `ticker` Vigil (actif nu) n'existe pas : `DEFAULT_TRADING_SYMBOLS` et le champ `symbol` des trades stockent déjà des actifs nus (`'BTC'`, `'ETH'`...), identiques au format `ticker` de Vigil. Aucune couche de conversion ajoutée.

### Implémentation
- `apps/core/vigil_client.py` (nouveau) : `fetch_signals()` — GET `/api/signals` avec bearer token (`VIGIL_BEARER_TOKEN`), retombe toujours sur `[]` (jamais d'exception) si Vigil est mal configuré, indisponible, ou renvoie une réponse invalide — Vigil est une donnée d'agrément, pas un prérequis de fonctionnement.
- `config/settings.py` : `VIGIL_API_URL`, `VIGIL_BEARER_TOKEN`, `VIGIL_TIMEOUT_SECONDS` (défaut 5s), pas de `RuntimeError` si absents (contrairement à `API_CREDENTIAL_ENCRYPTION_KEY`).
- `apps/core/models.py` : `UserPreferences.tracked_assets` (JSONField, liste de strings, `default=list`). Migration `core.0018_userpreferences_tracked_assets`.
- `apps/dashboard/forms.py::UserStrategyForm` : champ `tracked_assets` (`MultipleChoiceField` + `CheckboxSelectMultiple`, options = `DEFAULT_TRADING_SYMBOLS` réutilisé depuis `apps.live_trading.views`, pas dupliqué) ; `save()` surchargé pour assigner la liste au `JSONField` (hors `ModelForm.Meta.fields` pour éviter la génération automatique de widget sur un `JSONField`).
- `apps/dashboard/templates/dashboard/settings.html` + `static/css/investment.css` : section "Actifs suivis" (checkboxes) dans le formulaire Stratégie existant.
- `apps/live_trading/views.py::vigil_signals_json` (+ route `vigil-signals.json`) : **un seul appel** `fetch_signals()` par chargement de page (jamais un appel par actif suivi, pour ménager le rate limit Vigil partagé entre utilisateurs Tradiaries) ; filtre `ticker in tracked_assets or ticker is None` ; n'expose que `source`/`ticker`/`summary`/`timestamp`/`reliability_tier` au JSON — jamais `raw_payload`/`news_score` bruts.
- `apps/live_trading/templates/live_trading/live_trading.html` + `static/css/trading.css` : bandeau (`#vigilSignalsBanner`), un seul `fetch()` au chargement (pas de polling), rendu de cards neutres (résumé + source + badge de fiabilité textuel "Fait vérifié"/"Donnée quantitative"/"Analyse" selon `reliability_tier` — jamais de code couleur directionnel ni de CTA d'action, conformément au Challenge), scroll horizontal manuel (`overflow-x: auto` + `scroll-snap`, pas d'auto-scroll JS), construction DOM via `textContent` (jamais `innerHTML` sur du contenu Vigil, pour éviter tout risque d'injection depuis une source tierce).

### Tests
- `apps/core/tests.py::VigilClientTests` (5 tests) : URL non configurée, bearer token envoyé, erreur réseau, JSON invalide, absence d'en-tête `Authorization` si token non configuré — tous mockés au niveau `requests.get` (haut niveau, cohérent avec `KrakenClientTests`).
- `apps/live_trading/tests.py::VigilSignalsJsonViewTests` (3 tests) : filtrage actifs suivis + signaux macro toujours inclus, `raw_payload` jamais exposé, réponse vide si Vigil indisponible, comportement sans préférences enregistrées.
- `apps/dashboard/tests.py::SaveStrategyViewTests` (+2 tests) : persistance de `tracked_assets`, liste vide si aucune case cochée.
- Suite complète : 95 tests, tous verts (`python manage.py test`).

### Vérification manuelle
- Serveur de dev + utilisateur de test temporaire (`vigil_manual_check`, supprimé après coup) : page Trading (200, bandeau masqué par défaut car `VIGIL_API_URL` non configuré en local), page Paramètres (200, 10 checkboxes d'actifs affichées), sauvegarde de la stratégie + 2 actifs suivis via le formulaire réel (persistance vérifiée en base), endpoint `vigil-signals.json` répond `{"signals": []}` sans erreur.
- ⚠️ Bug préexistant découvert au passage (sans lien avec ce chantier) : la migration `core.0017_apicredentialauditlog` (session du 2026-09-22) n'était pas appliquée sur `db.sqlite3` local — corrigé en lançant `python manage.py migrate` (routine, aucune perte de données). Le extension navigateur Claude in Chrome n'était pas connectée cette session : vérification faite via `curl` + utilisateur de test plutôt qu'en navigateur graphique.
- Non couvert par les tests automatisés (comme le drag & drop TP/SL) : rendu visuel réel du scroll horizontal du bandeau — à valider en navigateur dès que possible.

**Fichiers modifiés/créés** : `apps/core/vigil_client.py` (nouveau), `apps/core/models.py`, `apps/core/migrations/0018_userpreferences_tracked_assets.py` (nouveau), `apps/core/tests.py`, `config/settings.py`, `apps/dashboard/forms.py`, `apps/dashboard/templates/dashboard/settings.html`, `apps/dashboard/tests.py`, `apps/live_trading/views.py`, `apps/live_trading/urls.py`, `apps/live_trading/templates/live_trading/live_trading.html`, `apps/live_trading/tests.py`, `static/css/investment.css`, `static/css/trading.css`, `docs/plan-integration-vigil-2026-09-25.md` (nouveau).

---

## 2026-09-24 | PLANNING | Analyse critique d'intégration Vigil (API marché crypto)

### Contexte
Évaluation complète de l'intégration de Vigil (API Flask surveillance marché) dans Tradiaries (Django trading multi-user). Vigil agrège signaux de 7 sources (news, ETF, on-chain, prix, DeFi). Objectif : identifier points critiques, risques, et décisions requises avant Phase 2 (invite-only).

### Livrables
1. **Artifact** `vigil-integration-analysis.md` : analyse complète 9 domaines, matrice risques P0-P3, 20+ questions pour Vigil
2. **Challenge** (skill `/challenge`) : 6 points challengés activement
   - Auth via `login_required` suffisante? (Bearer token recommandé)
   - Secrets API Vigil chiffrés? (audit code requis)
   - Routes par source déjà existantes (clarification besoin)
   - Rate limiting où? (server-side recommandé)
   - Cache par user ou global? (Tradiaries propriétaire recommandé)
   - Render free performance? (benchmark requis)
3. **Summary .md** `vigil-tradiaries-challenge-summary.md` : résumé challenge partageable avec IA Vigil dédiée

### Décisions sorties du Challenge
**À trancher via `/gel-decision`** :
- Bearer token Vigil obligatoire ou optionnel?
- Rate limit par source ou global?
- Cache TTL Tradiaries (5 min ok pour news/prix?)?
- Appel monolithe `/api/signals` vs granulaire `/api/signals/<source>`?

### Blocages avant Phase 2
- 🔴 P0 : Vérifier chiffrement secrets API Vigil (crypto.cv, Binance, Etherscan) en base
- 🔴 P0 : Bearer token Vigil oui/non?
- 🟡 P1 : Rate limiting Vigil-side implementation
- 🟡 P1 : Benchmark latency Render free (sources parallèles)

### Non implémenté (hors périmètre session)
- Code client Vigil dans Tradiaries (prochaine étape)
- Route per-source dans Vigil (déjà existante)
- Cache Tradiaries (prochaine étape)

**Fichiers modifiés/créés** : 
- `docs/API_DOCUMENTATION.md` (lu, analyse)
- `/artifact/vigil-integration-analysis.md` (artifact public, 2ZWmtuDS4JeCzYw7pnrTEU)
- `F:\ToutPleinDeTrucs\Dev\Python\Vigil\docs\vigil-tradiaries-challenge-summary.md` (nouveau, pour IA Vigil)

---

## 2026-09-22 | AUDIT | Production Readiness Check (branche `dev`)

### Contexte
Check de préparation prod via `/prod-check` (le `SKILL.md` correspondant est incomplet/tronqué — critères bloquants appliqués au jugement, en s'appuyant sur `/security-review` comme demandé). Rapport complet : `docs/prod-check-2026-09-22.md`.

### Verdict
🟠 READY WITH WARNINGS pour Phase 1 (personnel) — 🔴 NOT READY pour toute ouverture à des utilisateurs non explicitement invités.

### Points bloquants identifiés
- **B1** : travail de la session (migration `0017`, audit trail, tests renforcés) non commité au moment du check — rien n'est encore déployable.
- **B2 (nouveau, non corrigé)** : `accounts/signup/` est un endpoint d'inscription totalement public (aucune invitation/validation), ce qui contredit la prémisse "invite-only" sur laquelle repose la décision de garder une clé Fernet unique pour toute l'instance (`decisions.md`, "Gestion des secrets API", 2026-09-22). Ajouté en décision en suspens.

### Points positifs confirmés
- Les 3 P0 de l'audit précédent (`docs/audit-production.md`, 2026-09-10) sont corrigés : machine d'états `KrakenOrderAttempt`, retry désactivé sur ordres Kraken non-idempotents, verrou atomique `is_closing`.
- Isolation multi-utilisateur vérifiée par grep exhaustif sur tous les `views.py` : aucune fuite trouvée.
- Déchiffrement Fernet invalide désormais loggé ; unicité clé Kraken imposée au niveau formulaire (2 points P1 de l'ancien audit, corrigés depuis).
- `check --deploy`, `makemigrations --check`, suite complète (85 tests) : tous propres.

**Fichiers modifiés** : `docs/prod-check-2026-09-22.md` (nouveau), `.ai/decisions.md`

---

## 2026-09-22 | TESTING | Renforcement de la suite de tests (watcher, kraken_client, portfolio_service, dashboard)

### Décision implémentée
Suite au plan `docs/testing-plan-2026-09-22.md` (découlant de `.ai/decisions.md` → "Amélioration du testing" et "Ordres futures LIVE via l'API Kraken Futures" — explicitement écartée de ce chantier) : 4 missions de tests, mocks haut niveau uniquement (aucun mock sur `requests`/`_sign()`).

### Implémentation (tests uniquement, aucun changement de comportement)
- **Mission 1 — Watcher** : `WatchTpSlCommandTests` (4 tests) sur `watch_tp_sl.py` — `--once`, heartbeat mis à jour après cycle réussi, **non** mis à jour après cycle en échec, `--interval` transmis à `time.sleep`.
  - ⚠️ Bug réel découvert en écrivant ces tests (non corrigé, hors périmètre de ce chantier — à traiter via `/debogage`) : le message de succès du watcher contient un caractère `✓` non encodable en `cp1252` (console Windows par défaut). Sur un tel environnement, un cycle **réussi** lève une `UnicodeEncodeError` lors du `stdout.write`, tombe dans le `except Exception` générique, et se retrouve donc traité comme un cycle en échec — le heartbeat n'est alors jamais mis à jour malgré un TP/SL correctement clôturé. Sans impact en prod (Railway = Linux/UTF-8) mais à corriger si un environnement Windows sert un jour de watcher.
- **Mission 2 — `kraken_client.py`** : `KrakenClientTests` (15 tests) — `add_spot_order` (payload construit, validations side/price/txid, `validate`/`userref`), `query_orders`, `fetch_order_fill_price`, `cancel_order`, et `_private_request` (clés absentes, erreur Kraken, JSON invalide), mocké au niveau `_private_request`/`_public_request`/`_get_kraken_credentials`/`_http_session` — jamais `requests` ni `_sign()` directement.
- **Mission 3 — `portfolio_service.py`** : `PortfolioServiceTests` (10 tests) — stats vides, netting achat/vente, filtre `trade_mode`, PnL réalisé/non réalisé spot et futures (LONG/SHORT), exclusion des positions PAPER dans `compute_global_stats`/`build_chart_series`, isolation multi-utilisateur, ventilation `by_strategy`, `win_rate`/`profit_factor` à `None` sans trade clôturé.
- **Mission 4 — `apps/dashboard/views.py`** : 8 nouveaux tests — accès dashboard protégé par login, inscription + connexion automatique, sauvegarde de stratégie scopée par utilisateur, création/suppression de `ApiCredential` scopées par utilisateur (404 sur la clé d'un autre utilisateur, pas 403 — cohérent avec le pattern IDOR déjà en place).

### Tests
- Suite complète du projet : **85 tests, tous verts** (`python manage.py test`).

**Fichiers modifiés** : `apps/core/tests.py`, `apps/dashboard/tests.py`, `docs/testing-plan-2026-09-22.md` (nouveau)

---

## 2026-09-22 | SECURITY | Audit trail des accès aux clés API (`ApiCredential`)

### Décision implémentée
Suite à la décision gelée "Gestion des secrets API — Chiffrement Fernet + Audit trail renforcée" (2026-09-22, `.ai/decisions.md`) : la clé Fernet unique est conservée (suffisante en invite-only), mais chaque accès à un `ApiCredential` (lecture du secret déchiffré, création, suppression) est désormais tracé pour permettre de détecter une compromission.

### Implémentation
- `apps/core/models.py` : nouveau modèle `ApiCredentialAuditLog(credential, user, platform, action, created_at)` — `credential` en `SET_NULL` pour que la trace survive à la suppression de la clé (platform/user conservés). Nouvelle méthode `ApiCredential.log_access(action)`.
- `ApiCredential.masked_api_key()` (affichage page Paramètres) trace un accès `READ` à chaque déchiffrement.
- `apps/core/kraken_client.py` : `_get_kraken_credentials()` trace un accès `READ` à chaque utilisation des clés pour un appel Kraken.
- `apps/dashboard/views.py` : `create_api_credential` trace `CREATE`, `delete_api_credential` trace `DELETE` (avant suppression effective).
- `apps/core/admin.py` : `ApiCredentialAuditLogAdmin` en lecture seule (list_display/filter par date, plateforme, action, utilisateur).
- Migration `core.0017_apicredentialauditlog`.

### Tests
- `apps/core/tests.py::ApiCredentialAuditTests` (5 tests) : lecture via `masked_api_key()`, lecture via `kraken_client`, survie de la trace après suppression de la clé, et les deux vues (création/suppression) via le client de test.
- Suite complète `apps.core apps.live_trading apps.dashboard` : 41 tests, tous verts.

**Fichiers modifiés** : `apps/core/models.py`, `apps/core/kraken_client.py`, `apps/core/admin.py`, `apps/core/tests.py`, `apps/dashboard/views.py`, `apps/core/migrations/0017_apicredentialauditlog.py`

---

## 2026-09-21 | FEATURE | Page Positions limitée aux positions clôturées ; positions ouvertes réservées à la page Trading

### Décision clarifiée avec l'utilisateur
La page Investissements (`apps/investment`, modèle `SimpleInvestment`) n'a pas de notion d'ouvert/fermé (pas de `exit_price`, chaque ligne est déjà une transaction complète) : laissée inchangée sur demande explicite de l'utilisateur. Seule la page Positions (Spot/Futures) est concernée.

### Implémentation
- `apps/positions/views.py` : `trades` filtré par `exit_price__isnull=False` pour les deux catégories (SPOT et FUTURES). Les KPI (`compute_spot_stats`/`compute_futures_stats`) restent calculés sur l'ensemble du portefeuille (ouvertes + fermées), seule la liste affichée change.
- `apps/positions/templates/positions/positions.html` : texte d'intro et état vide mis à jour pour préciser que les positions ouvertes sont désormais sur la page Trading.
- La page Trading (`apps/live_trading`) affichait déjà les positions ouvertes en temps réel dans la section "Positions ouvertes" sous le graphique (`live_positions()`, filtré `exit_price__isnull=True`) — aucun changement nécessaire de ce côté, l'exigence était déjà satisfaite.

### Tests
- `apps/positions/tests.py` : tests existants adaptés (les trades de test sont désormais créés avec `exit_price` pour rester visibles) + nouveau test `test_open_positions_are_excluded` couvrant explicitement l'exclusion des positions ouvertes (Spot et Futures) de la page.
- Suite complète : `python manage.py test` → 43 tests, tous verts.

### Vérification
- Serveur de dev + compte de test temporaire (supprimé après coup, ainsi que les positions de test créées) : page Positions (onglets Spot/Futures) n'affiche que les positions clôturées ; page Trading affiche bien les positions ouvertes restantes sous le graphique. Aucune erreur console.

**Fichiers modifiés** : `apps/positions/views.py`, `apps/positions/templates/positions/positions.html`, `apps/positions/tests.py`

---

## 2026-09-21 | FEATURE | Synchronisation du déplacement horizontal (pan/zoom) entre le graphique prix et le graphique volume/MM20

### Contexte
`chart` (prix/SAR) et `volumeChart` (volume/MM20) sont deux instances lightweight-charts indépendantes ; chacune gérait son propre pan/zoom sans lien avec l'autre, rendant la lecture croisée prix/volume malaisée dès qu'on naviguait sur le graphique.

### Implémentation
- `apps/live_trading/templates/live_trading/live_trading.html` : ajout de `syncTimeScale(source, target)`, qui s'abonne à `source.timeScale().subscribeVisibleLogicalRangeChange` et répercute la plage logique visible sur `target.timeScale().setVisibleLogicalRange(range)`. Abonnement bidirectionnel (`chart` → `volumeChart` et `volumeChart` → `chart`), avec un verrou `isSyncingTimeScale` pour éviter la boucle infinie de rappels croisés.
- `loadChart()` : suppression de l'appel `volumeChart.timeScale().fitContent()`, devenu redondant — le `fitContent()` sur `chart` déclenche désormais la synchronisation qui aligne `volumeChart` automatiquement.

### Vérification
- Serveur de dev + compte de test temporaire (supprimé après coup).
- Glisser-déposer (pan) sur le graphique prix → le graphique volume suit exactement la même plage visible, et inversement (testé dans les deux sens).
- Molette (zoom) sur le graphique prix → le graphique volume zoome en cohérence.
- Changement d'intervalle (1h → 4h) : les deux graphiques rechargent et s'alignent correctement après `fitContent()`.
- Aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

---

## 2026-09-21 | BUGFIX | Calcul du SAR faussé : convergeait vers une asymptote horizontale fixe

### Cause réelle
Dans `calculateSAR`, la variable `ep` (extreme point — le plus haut/plus bas atteint pendant la tendance en cours, utilisé dans la formule `SAR += AF * (EP - SAR)`) n'était **jamais mise à jour pendant la poursuite d'une tendance**. Le code maintenait bien des variables `hp`/`lp` séparées pour suivre les nouveaux extrêmes, mais celles-ci ne servaient qu'à initialiser le SAR lors d'un retournement de tendance — la formule de récurrence continuait, elle, à utiliser l'`ep` figé à sa valeur initiale (le plus haut/bas de la toute première bougie). Résultat : `SAR += AF * (EP_fixe - SAR)` est une suite contractante qui converge mathématiquement vers `EP_fixe`, d'où l'asymptote horizontale observée à 77530.30 (prix de la première bougie visible).

### Correctif (conforme à l'algorithme Wilder standard, tel qu'utilisé par TradingView `ta.sar`)
- `apps/live_trading/templates/live_trading/live_trading.html`, fonction `calculateSAR` :
  - Suppression des variables `hp`/`lp` redondantes ; `ep` est désormais mis à jour à chaque nouveau plus haut (tendance haussière) / plus bas (tendance baissière), avec incrémentation de l'AF à ce moment précis (comportement Wilder standard).
  - Clamp du SAR calculé par le min/max des deux bougies précédentes (`prev`, `prev2`) au lieu d'inclure à tort la bougie courante dans le clamp.
  - Lors d'un retournement, le nouveau SAR repart bien de l'`ep` de la tendance qui se termine (comportement inchangé, déjà correct).

### Vérification
- Serveur de dev + compte de test temporaire (supprimé après coup).
- `sarSeries.data()` : 193 valeurs distinctes sur 200 points (au lieu de converger vers une valeur quasi constante), min/max cohérents avec la plage de prix affichée, SAR bascule visiblement au-dessus/en-dessous des bougies aux retournements.
- Aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

---

## 2026-09-21 | FEATURE | Moyenne mobile 20 (ligne) sur le graphique de volume

### Implémentation
- `apps/live_trading/templates/live_trading/live_trading.html` :
  - Nouvelle fonction `calculateSMA(points, period)` (moyenne mobile simple générique, fenêtre glissante).
  - Nouvelle série `volumeMaSeries` (`volumeChart.addLineSeries`, couleur bleu clair `#8ec1ff`) superposée à l'histogramme de volume existant.
  - `loadChart()` calcule `calculateSMA(volume, 20)` et l'injecte via `volumeMaSeries.setData(...)` à chaque chargement/changement d'actif ou d'intervalle.

### Vérification
- `volumeMaSeries.data()` : 181 points pour 200 bougies (200 − 19, cohérent avec une SMA20 qui démarre au 20e point).
- Ligne bleue visible superposée à l'histogramme de volume dans le navigateur, aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

---

## 2026-09-21 | FEATURE | SAR affiché en points (style TradingView) au lieu d'une courbe pointillée

### Implémentation
- `apps/live_trading/templates/live_trading/live_trading.html` : `sarSeries` (lightweight-charts) passe de `addLineSeries({ lineStyle: Dotted })` (courbe continue en pointillés) à `addLineSeries({ lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2 })` — n'affiche que des points ronds disjoints à chaque valeur SAR calculée, sans segment reliant les points.
- Calcul du SAR (`calculateSAR`) inchangé.

### Vérification
- Serveur de dev + compte de test temporaire (supprimé après coup) : SAR affiché en points jaunes disjoints sur le graphique BTC, aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

---

## 2026-09-21 | BUGFIX | Drag & drop TP/SL intermittent : clic-glissé simple réservé à la navigation, Maj+glissé pour déplacer TP/SL

### Cause réelle
Le correctif précédent (voir entrée BUGFIX suivante) rendait le glisser-déposer syntaxiquement correct, mais le clic-glissé simple restait en concurrence avec le comportement natif de lightweight-charts (`handleScroll.pressedMouseMove` / `handleScale`, activés par défaut) : un clic démarré près d'une ligne TP/SL pouvait être capté tantôt par notre handler, tantôt par le pan/zoom natif de la lib selon l'endroit exact du clic et le mouvement de la souris — d'où le comportement intermittent rapporté.

### Correctif
- `apps/live_trading/templates/live_trading/live_trading.html` :
  - Le clic-glissé simple sur le graphique n'est plus intercepté : il déclenche uniquement le comportement natif de la lib (pan/zoom).
  - Ajout d'un key binding **Maj + clic-glissé** : seul un `mousedown` avec `event.shiftKey` déclenche la détection de ligne (Entrée/TP/SL) et le déplacement.
  - Pendant un déplacement Maj+glissé, `chart.applyOptions({ handleScroll: false, handleScale: false })` désactive temporairement le pan/zoom natif pour éliminer toute concurrence entre les deux gestes ; ré-activé au `mouseup`.
  - Indice utilisateur sous le graphique mis à jour pour mentionner Maj+glissé.

### Vérification
- Serveur de dev + utilisateur de test temporaire (supprimé après coup).
- Clic-glissé simple sur une ligne TP : le graphique navigue (pan), le champ TP ne change pas (régression testée, OK).
- Maj+clic-glissé (simulé via dispatch d'événements `MouseEvent` avec `shiftKey: true`, le geste synthétique de l'outil de contrôle navigateur ne propageant pas le modificateur) sur la ligne TP : le champ se met à jour avec le nouveau prix.
- Après relâchement, `chart.options().handleScroll`/`handleScale` repassent à `true` (pan/zoom natif restauré).
- Aucune erreur console.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

---

## 2026-09-21 | BUGFIX | Drag & drop TP/SL sur le graphique Trading toujours inopérant

### Cause réelle
Le correctif précédent (voir entrée FEATURE ci-dessous) appelait `candleSeries.priceScale().priceToCoordinate()` / `.coordinateToPrice()`. Ces méthodes n'existent que sur l'API série (`ISeriesApi`), pas sur l'API échelle de prix (`IPriceScaleApi`, retournée par `.priceScale()`) — vérifié dans le bundle vendorisé `lightweight-charts.standalone.production.js` (classe `ge` : seulement `applyOptions`/`options`/`width`). L'appel levait une `TypeError` silencieuse à chaque `mousedown`/`mousemove`, empêchant `draggingField` d'être positionné : aucun glisser-déposer ne pouvait jamais démarrer.

### Correctif
- `apps/live_trading/templates/live_trading/live_trading.html` : remplacement par `candleSeries.priceToCoordinate(price)` et `candleSeries.coordinateToPrice(mouseY)` (méthodes de la série, pas de l'échelle de prix).

### Vérification
- Serveur de dev lancé localement, page `/live/` testée dans Chrome (utilisateur de test temporaire, supprimé après coup) : glisser-déposer des lignes **Take profit** et **Stop loss** confirmé fonctionnel (le champ associé se met à jour avec le nouveau prix). La ligne **Entrée** reste volontairement non-draggable tant que le champ est vide (placeholder "vide = marché") — comportement voulu, pas un bug.

**Fichiers modifiés** : `apps/live_trading/templates/live_trading/live_trading.html`

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
