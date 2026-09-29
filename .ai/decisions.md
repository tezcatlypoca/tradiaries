# Tradiaries — Décisions

**Dernière mise à jour** : 2026-09-25

## Décisions retenues ✅

### Multi-utilisateur (2026-09-14)
- **Décidé** : isolation complète des données par compte (chaque modèle métier a un `user` FK,
  chaque vue filtre/rattache par `request.user`) + page d'inscription publique (`accounts/signup/`).
- **Raison** : préparer l'intégration d'un futur coach IA ; l'audit du 2026-09-10 avait déjà identifié
  l'absence de propriétaire comme faille P1 (IDOR — tout compte pouvait voir/modifier les données
  d'un autre). Validé explicitement avec l'utilisateur avant implémentation (changement structurant
  touchant sécurité/authentification).
- **Impact** : migrations `core.0012/0013/0014` (backfill de l'historique existant vers le compte
  `samsan`) ; toutes les fonctions de `portfolio_service.py`/`trading_service.py`/`kraken_client.py`
  prennent désormais un `user` obligatoire ; `KrakenNonceCounter` devient un compteur par utilisateur ;
  `ApiCredential` unique par (utilisateur, plateforme) au lieu de globalement unique par plateforme.
- **Rattachement des données historiques** : tout l'historique (trades, clés API) est rattaché au
  superuser existant (`samsan`) — validé explicitement par l'utilisateur.
- **Watcher TP/SL** : reste un process global qui surveille les positions de TOUS les utilisateurs,
  mais chaque clôture LIVE utilise désormais les clés Kraken du propriétaire de la position (plus de
  clé globale partagée). Les clés Kraken déjà en place restent celles de `samsan` et ne sont PAS
  répliquées automatiquement pour les nouvelles inscriptions — chaque nouvel utilisateur doit
  renseigner ses propres clés depuis la page Paramètres avant de pouvoir trader en LIVE.
- **Hors périmètre explicite** : développement du module de coaching IA lui-même (demandé pour plus tard).

### Modèle Investment (2026-09-07)
- **Décidé** : `entry_date` = `default=timezone.now` (pas `auto_now_add`)
- **Raison** : Permet import dates historiques pour Spot/Futures
- **Impact** : Migration `0005_futurestrading_strategy_and_more`

### Dashboard stats (2026-09-07)
- **Décidé** : Dashboard = stats GLOBALES uniquement (Portfolio Value, Capital, PnL Global)
- **Raison** : Utilisateur a demandé de simplifier après première refonte avec détails par catégorie
- **Impact** : Chaque page catégorie calcule ses propres stats via `compute_*_stats()`

### Prix marché (2026-09-07)
- **Décidé** : Dashboard chart = cost basis cumulé, PAS mark-to-market historique
- **Raison** : Pas de source de prix passés, utilisateur préfère cost basis
- **Impact** : Graphique stable (pas de volatilité rétrospective)

### Trade mode LIVE/PAPER (2026-09-08)
- **Décidé** : FuturesTrading.trade_mode avec choix PAPER par défaut
- **Raison** : Tous les trades historiques étaient PAPER avant cette date
- **Impact** : Futures et Spot ont le mode, analytics/journal le filtrent

### Kraken API (2026-09-09)
- **Décidé** : ApiCredential chiffré (Fernet), clé unique par plateforme
- **Raison** : Secrets ne doivent jamais traîner en clair, pas de choix silencieux
- **Impact** : `kraken_client._get_kraken_credentials()` lit BDD (pas .env)
- **MAJ 2026-09-14** : l'unicité "une clé par plateforme" est désormais par (utilisateur, plateforme) suite à l'introduction du multi-utilisateur — voir décision "Multi-utilisateur".

### HTTPS production (2026-09-10)
- **Décidé** : `RuntimeError` si `DEBUG=False` sans SECURE_SSL_REDIRECT/SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE
- **Raison** : Éviter lockout accidentel lors du déploiement en prod
- **Impact** : Railway doit avoir mêmes vars de sécurité que Render

### Nonce Kraken (2026-09-10)
- **Décidé** : Compteur DB (KrakenNonceCounter) incrémenté sous `select_for_update()`
- **Raison** : Multi-worker/process-safe, évite collisions timestamp
- **Impact** : Requis pour concurrence > 1 worker

### Close position concurrence (2026-09-10)
- **Décidé** : `is_closing` booléen + `select_for_update()` atomique
- **Raison** : Éviter double-clôture si deux requêtes TP/SL simultanées
- **Impact** : Verrou relâché (finally) si clôture échoue pour retry suivant

### CSS architecture (2026-09-12)
- **Décidé** : Séparation layout (style.css) vs styling menu (side-menu.css)
- **Raison** : Éviter dépendances circulaires et bugs d'état menu
- **Impact** : style.css charge AVANT side-menu.css dans tous les templates

### Menu persistance (2026-09-12)
- **Décidé** : localStorage `tradiaries-menu-state`, initialisation SANS animation (classe `.initializing`)
- **Raison** : Éviter flicker au rechargement, état cohérent par appareil
- **Impact** : Menu reste fermé en mobile après navigation par tabs

### PWA Icon Candlestick (2026-09-12)
- **Décidé** : Icône candlestick (OHLC + uptrend), SVG + PNG 192×192/512×512
- **Raison** : Représente trading/chandeliers (domaine métier), modern + installable PWA
- **Impact** : Généré via cairosvg, manifest updated (theme_color #10b981), tous templates updated
- **Génération** : Script `utils/generate_pwa_icons.py` pour future régénération

---

## Décisions retenues ✅

### Gestion des secrets API — Chiffrement Fernet + Audit trail renforcée (2026-09-22)
- **Décidé** : Garder la solution actuelle (clé Fernet unique dérivée de `SECRET_KEY` pour toute l'instance) ET ajouter un **audit trail renforcé** pour enregistrer tous les accès à `ApiCredential` (lectures/créations/suppressions).
- **Raison** : La clé unique est suffisante pour un modèle invite-only / petit pool de traders (confiance élevée). L'audit trail donne la visibilité nécessaire pour détecter une compromission (« Qui a accédé à quelle clé Kraken et quand »).
- **Implémentation audit trail** : Ajouter `accessed_at` / `last_read_at` sur `ApiCredential` ou un modèle séparé `ApiCredentialAuditLog(credential, user, action, timestamp)`.
- **Conditions de activation** : Reste valide tant que le modèle reste **invite-only** ou **tier restreint**. Basculer vers clé per-user + external vault si ouverture large (voir en suspens ci-dessous).

### Amélioration du testing — nouveaux tests + intégration BDD/API (2026-09-22)
- **Décidé** : Ajouter de nouveaux tests unitaires et d'intégration en gardant l'approche déjà en place : `TestCase` Django (BDD réelle SQLite en transaction) + mocks **haut niveau** sur les fonctions `kraken_client`/`trading_service` (ex. `@patch('...fetch_current_price')`, `@patch('...add_spot_order')`), sans introduire de mocks bas niveau sur `requests`/`_sign()`/`_private_request()`.
- **Raison** : Cohérent avec la suite existante (35 tests `apps/core`, 2 `apps/dashboard`), pas de changement d'approche à justifier. Le mock bas niveau proposé en Challenge (vérifier le payload réellement envoyé à Kraken via `_sign`/`_private_request`) est explicitement écarté pour l'instant — voir rejetée ci-dessous.
- **Zones prioritaires identifiées en Challenge, à couvrir en premier** :
  - `apps/core/management/commands/watch_tp_sl.py` (la boucle watcher elle-même — actuellement seule `check_tp_sl()` est testée, pas la commande/heartbeat/isolation d'erreurs)
  - `kraken_client.py` : `add_spot_order`, `query_orders`, `cancel_order`, `fetch_order_fill_price` (pas de test direct trouvé, seulement via mock dans `trading_service`)
  - `portfolio_service.py` (pas de classe de test dédiée trouvée hors `futures_trade_pnl`)
  - `apps/dashboard/views.py` (2 tests seulement, module modifié dans le diff en cours)
- **Impact** : Pas de changement d'architecture de test. Extension de `apps/core/tests.py` et `apps/dashboard/tests.py` avec de nouvelles classes ciblant ces zones.

### Intégration des news Vigil — Bandeau contextuel sur la page Trading (2026-09-25)
- **Décidé** : Afficher les signaux Vigil sous forme de **bandeau de cards à défilement horizontal manuel** (pas d'auto-scroll) sur la page Trading (`apps/live_trading`). Pas de page/table séparée pour parcourir le flux Vigil en v1.
- **Filtrage** : liste d'actifs suivis déclarée par l'utilisateur dans Paramètres (nouveau champ structuré, aux côtés du champ `strategy` déjà présent sur `UserPreferences`) + signaux macro/géopolitiques généraux (`ticker=null`) toujours affichés, indépendamment de cette liste.
- **Raison** : le seul besoin identifié en Challenge est de contextualiser une prise de trade en cours, pas de parcourir un flux de news général. L'auto-scroll a été explicitement écarté pour ne pas distraire l'utilisateur pendant la validation d'un ordre LIVE (cohérent avec la checklist IRC déjà en place).
- **Affichage neutre obligatoire** (issu du Challenge, pour limiter le risque de lecture comme conseil financier déguisé) : pas de code couleur directionnel (vert/rouge façon signal bull/bear), pas de CTA orienté action, `reliability_tier` Vigil toujours visible pour distinguer fait (GROUND_TRUTH/QUANTITATIVE) d'opinion (EDITORIAL).
- **Impact** : nouveau champ structuré sur `UserPreferences` (liste d'actifs suivis — format à préciser en Planification), nouveau composant JS sur `live_trading.html`, mapping requis entre `symbol` Tradiaries (format paire exchange, ex. `XBTUSD`) et `ticker` Vigil (actif nu, ex. `BTC`). Client HTTP Vigil : bearer token partagé (`VIGIL_BEARER_TOKEN`), pas de cache Tradiaries nécessaire pour protéger Vigil (ingestion 100% cron côté Vigil, lecture instantanée) — un cache reste à envisager plus tard uniquement si le rate limit partagé (30/min, un seul token pour tous les utilisateurs Tradiaries) devient limitant en Phase 2.
- **RÉVISÉ le 2026-09-27** : `vigil_signals_json` expose désormais aussi `impact_score`/`news_score` (importance par timeframe, novelty, source_count) dans une vue détaillée cliquable depuis chaque card (résumé complet + scores repliés par défaut sous un `<details>`/spoiler). Revient sur l'exclusion initiale de `news_score` du JSON (« jamais de `raw_payload`/`news_score` bruts »), demandée explicitement par l'utilisateur pour cette vue détaillée. `raw_payload` reste, lui, jamais exposé (identifiants d'article/payload brut de la source, pas un score). Le principe d'affichage neutre (pas de code couleur directionnel, pas de CTA) reste inchangé : les scores ajoutés sont des mesures de fiabilité/nouveauté/impact, pas des signaux bull/bear.

## Décisions rejetées ❌

### Table/page dédiée aux news Vigil en v1 (2026-09-25)
- **Rejeté** : Pas de vue table séparée pour parcourir l'ensemble des signaux Vigil en v1 — seul le bandeau contextuel sur la page Trading est construit.
- **Raison** : aucun besoin distinct de la contextualisation sur la page Trading n'a été identifié ; construire les deux composants (bandeau + table) pour un seul besoin réel aurait été de la sur-ingénierie.
- **Où revisiter** : si un besoin de consultation libre du flux Vigil (hors contexte d'une prise de trade) émerge après usage du bandeau.

### Ordres futures LIVE via l'API Kraken Futures (2026-09-22)
- **Rejeté (pour l'instant)** : Ne pas implémenter/valider de passage d'ordres futures LIVE via l'API Kraken Futures dans cette session. Rester exclusivement sur l'API Kraken **spot/classic** déjà en place.
- **Raison** : L'API Kraken Futures (`futures.kraken.com`) est un système distinct de l'API spot déjà implémentée (`api.kraken.com`) — authentification différente, compte séparé (marge/levier), symboles différents (`PF_XBTUSD`), et aucune réutilisation directe de `_sign()`/`_private_request()`/`ApiCredential(platform='KRAKEN')` en l'état. Ce n'est pas une extension de `kraken_client.py`, c'est un nouveau client à construire. `trading_service.py` refuse déjà explicitement le LIVE futures (`TradeMode.LIVE` + `category='FUTURES'` → `TradingError`), ce qui est cohérent avec la décision "Modèle de déploiement progressif" (2026-09-22) : le LIVE réel n'est un critère que de Phase 2, et l'app est actuellement en Phase 1 (perso, un seul utilisateur).
- **Où revisiter** : Si besoin de valider la faisabilité technique de l'API Kraken Futures, le faire via un spike isolé hors de l'app Django (script séparé, clés Futures dédiées) sans toucher `trading_service.py`/`open_position()` — voir décision "Modèle de déploiement progressif".

## Décisions en suspens ⏳

### Geste tactile pour déplacer TP/SL sur le graphique Trading (2026-09-25, découvert en `/implementation` responsive)
- **Question** : Le déplacement des lignes Entrée/TP/SL sur le graphique de la page Trading utilise `Maj + clic-glissé` sur desktop (`live_trading.html`, `event.shiftKey`) — il n'existe pas d'équivalent tactile (pas de touche Maj sur un écran tactile), donc impossible de déplacer TP/SL directement sur le graphique en mobile/tablette. Faut-il ajouter un geste alternatif (ex. appui long) ou assumer que cette interaction reste desktop uniquement ?
- **Contexte** : identifié lors de la refonte responsive tablette/smartphone du 2026-09-25 (`docs/plan-responsive-smartphone-2026-09-25.md`). La saisie manuelle des valeurs TP/SL via les champs du formulaire reste possible sur tous les appareils — ce n'est pas un blocage fonctionnel, juste une perte de confort sur mobile/tablette.
- **Impact si retenu** : chantier d'interaction distinct (détection appui long, éventuellement rebalayage du geste desktop existant), hors périmètre visuel de la refonte responsive déjà livrée.
- **Décision** : non tranchée — à trancher séparément, pas bloquant.

### Champ `timeframe` : texte libre vs liste prédéfinie (2026-09-25)
- **Question** : Faut-il convertir `Investment.timeframe` (actuellement `CharField` texte libre, hérité par `SpotTrading`/`FuturesTrading`) en liste de choix fermée ?
- **Contexte** : nécessaire pour mapper fiablement le timeframe d'un trade vers les buckets `news_score.importance` de Vigil (`intraday`/`swing`/`position`) et affiner la pertinence des news affichées dans le bandeau Trading. Texte libre = valeurs hétérogènes, mapping non fiable en l'état. Évoqué comme possible par l'utilisateur, non tranché.
- **Impact si retenu** : nouvelle migration sur `SpotTrading`/`FuturesTrading` (le champ existe déjà via migration `0015`), mise à jour des formulaires/modals Spot et Futures.
- **Décision** : à trancher en Planification ou dans une session dédiée, pas bloquant pour démarrer le bandeau Vigil (le filtrage par liste d'actifs suivis ne dépend pas de ce champ).

### Commercialisation potentielle de Tradiaries (2026-09-25)
- **Question** : L'utilisateur envisage de commercialiser Tradiaries pour d'autres traders retail si l'usage personnel s'avère concluant — à quel moment et sous quelle forme ?
- **Contexte** : ne change rien à trancher immédiatement sur l'intégration Vigil, mais recoupe directement la décision existante "Modèle de déploiement progressif" (Phase 3 = grand public/abonnement, ci-dessous) et le critère de bascule de "Clé Fernet par utilisateur + External Key Vault" (déjà conditionné à une "ouverture grand public"). Le Cadrage du projet (`project-context.md`) décrit toujours Tradiaries comme "application Django personnelle" — à mettre à jour explicitement le jour où cette intention se précise.
- **Décision** : aucune action requise maintenant. À re-challenger avec une grille concurrentielle (TraderSync/Cypher, TradesViz — déjà identifiés dans `docs/coach-ia-vers-tradiaries-2026-09-25.md` comme concurrents sur la détection de violation de règle) le jour où l'intention de commercialisation se précise.

### Inscription publique (`accounts/signup/`) vs modèle "invite-only" (2026-09-22, trouvé en `/prod-check`)
- **Question** : Faut-il fermer l'inscription publique (`SignupForm` n'exige aujourd'hui aucune invitation/validation), ou ajouter un vrai mécanisme d'invitation (code à usage unique, approbation admin) ?
- **Contexte** : La décision "Gestion des secrets API" (2026-09-22, ci-dessus) justifie la clé Fernet **unique pour toute l'instance** par un modèle "invite-only / petit pool de traders (confiance élevée)". Or le code actuel contredit déjà cette prémisse : n'importe qui peut créer un compte sur `accounts/signup/` sans invitation et y attacher de vraies clés Kraken LIVE. Une fuite de `SECRET_KEY` compromettrait donc les clés de tous les comptes, y compris ceux créés librement par des inconnus — pas seulement celles d'un petit cercle de confiance.
- **Options** :
  - A) Fermer `accounts/signup/` (redirect/403) tant que le modèle reste invite-only de fait.
  - B) Ajouter un vrai mécanisme d'invitation (code à usage unique généré par l'utilisateur/admin, ou approbation manuelle des nouveaux comptes).
  - C) Assumer l'ouverture publique dès maintenant et anticiper la décision "Clé Fernet par utilisateur + External Key Vault" ci-dessous.
- **Décision** : À trancher avant toute exposition non contrôlée de l'app (voir `docs/prod-check-2026-09-22.md`).

### Clé de chiffrement Fernet par utilisateur + External Key Vault
- **Question** : Quand migrer de la clé unique vers une clé dérivée par utilisateur (ou external vault) pour `ApiCredential` ?
- **Contexte** : Pré-requis futur pour une **ouverture publique large** (landing page, inscription libre, base utilisateurs à 3+ chiffres en LIVE) pour isoler complètement les secrets d'un utilisateur des autres en cas de fuite `SECRET_KEY`.
- **Options évaluées** :
  - A) Clé per-user dérivée (PBKDF2/Argon2 de password ou user.id) : complexité moyenne, pas vraiment plus sûr si `SECRET_KEY` compromise.
  - B) External Key Vault (HashiCorp Vault / AWS KMS / Google Cloud Secret Manager) : vraie séparation, audit natif, but overkill pour MVP.
  - C) Status quo (clé unique) + audit trail : suffisant pour invite-only.
- **Critère de basculement** : Si tu atteins 50+ utilisateurs LIVE avec vrais secrets Kraken, ou si tu reçois une demande de conformité (GDPR, SOC2, etc.), re-trancher vers option A ou B.
- **Décision** : À revisiter avant ouverture grand public.

### Affichage `strategy` dans la table futures_trading.html — REJETÉE (2026-09-22)
- **Décidé** : NE PAS afficher `strategy` en colonne dans la table futures_trading.html
- **Raison** : Le modal détail donne accès instantané à la stratégie pour les trades qui en ont besoin. Scanner la stratégie dans la liste n'est pas un cas d'usage réel — consulter un trade spécifique via le détail modal suffit.
- **Où afficher `strategy`** : Conservé en journal.html et analytics.html (où il aide à filtrer/analyser les historiques)
- **Impact** : Pas de changement de code nécessaire. La table futures_trading reste comme elle est.

### Modèle de déploiement progressif (2026-09-22)
- **Décidé** : Trois phases de déploiement, chacune avec exigences de sécurité/test alignées au scope :
  1. **Phase 1 (actuellement)** : Déploiement personnel (Render public, une seule personne). Scope : développement du concept et fonctionnalités. Exigences : tests unitaires/intégration + vérifications manuelles basiques.
  2. **Phase 2 (futur)** : Bêta invite-only (autres utilisateurs). Scope : validation UX/sécurité avant ouverture publique. Avant phase 2 : /code-review ultra + /security-review (branche `prod`), PWA test iOS/Android, 1 ordre Kraken LIVE réel testé.
  3. **Phase 3 (futur)** : Grand public abonnement. Scope : produit commercial. Exigences : SOC2, compliance, monitoring/alerting complets, clé Fernet per-user + external vault, rate limiting Kraken.
- **Gating vers phase 2** : Code review + security review obligatoires avant merge `dev` → `prod`
- **Gating vers phase 3** : Durcissement sécurité (voir décision "Clé Fernet par utilisateur + External Key Vault")
- **Implication immédiate** : Phase 1 est validée. PWA, Kraken LIVE test détaillé, monitoring avancé = Phase 2+. Pas de blocage pour continuer dev en phase 1.

---

## Débats non tranchés

### Whitenoise vs CDN
- **Pro Whitenoise** : Simple, pas de dépendance externe
- **Pro CDN** : Faster pour utilisateurs géo-éloignés
- **Current** : Whitenoise en prod
- **Revisit si** : Utilisateurs multiples en prod

### Service Worker precache vs network-first
- **Current** : Network-first pour HTML, cache-first pour /static/
- **Alternative** : Precache tous les assets (plus lourd)
- **Decision** : Éviter precache pour pas casser filenames hashés Whitenoise

### Base de données: Postgres vs SQLite
- **Current** : Neon Postgres serverless
- **SQLite** : Trop limité (serverless pas supporté, locks)
- **Locked in** : Postgres pour multi-worker + concurrence
