# Tradiaries — Project Context

**Dernière mise à jour** : 2026-09-27  
**État générale** : Fonctionnel en dev, PWA avec icon candlestick, UI trading refondue (drag & drop TP/SL fiabilisé, SAR corrigé, graphiques synchronisés), page Positions limitée aux positions clôturées, multi-utilisateur opérationnel, audit trail clés API, suite de tests renforcée (watcher/kraken_client/portfolio_service/dashboard), bandeau de news Vigil sur la page Trading (cards avec tag/titre cliquables, vue détaillée avec scores), refonte responsive tablette + smartphone (menu, tableaux, page Trading), 96 tests ✅. **Coach IA** : relocalisé de Vigil vers Tradiaries (voir `docs/coach-ia-vers-tradiaries-2026-09-25.md`), cadrage repris tel quel (v1 = rule-checker déterministe), pas encore démarré.

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

#### Bandeau news Vigil sur la page Trading (2026-09-25, complété 2026-09-27)
- ✅ (2026-09-27) Card cliquable : tag dérivé de la source (ex. "On-chain", "Éditorial") + titre (résumé) affichés, clic ouvre une vue détaillée (`<dialog>` natif) avec résumé complet, métadonnées, et un spoiler replié affichant `impact_score`/`news_score` (importance intraday/swing/position, nouveauté, sources corroborantes) — voir `decisions.md` pour la révision assumée de l'exposition des scores.
- ✅ `apps/core/vigil_client.py` : client HTTP Vigil (bearer token, dégradation gracieuse — `[]` si Vigil indisponible/mal configuré, jamais d'exception)
- ✅ `UserPreferences.tracked_assets` (JSONField) : liste d'actifs suivis, réglable dans Paramètres (checkboxes, réutilise `DEFAULT_TRADING_SYMBOLS`)
- ✅ Endpoint `vigil-signals.json` : un seul appel Vigil par chargement de page, filtré (actifs suivis + signaux macro/géopolitiques `ticker=null` toujours inclus) ; n'expose jamais `raw_payload`, mais expose désormais `impact_score`/`news_score` depuis le 2026-09-27 (voir ligne ci-dessus et `decisions.md`)
- ✅ Bandeau sur la page Trading : scroll horizontal **manuel** (pas d'auto-scroll), cards neutres (badge de fiabilité textuel, pas de code couleur directionnel, pas de CTA d'action) — voir Challenge/`decisions.md` du 2026-09-25 pour le raisonnement complet
- ✅ Tests : `VigilClientTests` (5), `VigilSignalsJsonViewTests` (4, +1 le 2026-09-27 pour les scores), 2 tests `SaveStrategyViewTests` — suite complète 96 tests, tous verts
- ✅ (2026-09-27) Rendu des cards + dialog de détail vérifié en navigateur (Claude in Chrome, compte de test temporaire, données Vigil mockées en JS) : tags/titre/scores s'affichent correctement, aucune erreur console
- 🟡 Non couvert par les tests automatisés : rendu visuel réel avec de vraies données Vigil (la vérification du 2026-09-27 utilise des signaux mockés côté client, pas un appel réel à une instance Vigil) ; scroll horizontal du bandeau avec plusieurs cards réelles pas revérifié depuis le 2026-09-25
- 🟡 (2026-09-27) Cause du bandeau vide en local identifiée et corrigée : `VIGIL_API_URL` locale sans préfixe `/api` (voir `change-log.md` 2026-09-27) — `.env.example` documente désormais ce préfixe requis. Vigil local confirmé opérationnel (news visibles côté interface de monitoring Vigil), mais rendu effectif du bandeau sur la page Trading après correctif pas encore confirmé par l'utilisateur
- **Hors périmètre de ce chantier** : Coach IA (aucune dépendance de code, seule l'API Vigil est partagée)

#### Refonte responsive tablette + smartphone (2026-09-25)
- ✅ Planification avec vérification visuelle live (Claude in Chrome, viewport simulé via harnais iframe) : `docs/plan-responsive-tablette-2026-09-25.md` / `docs/plan-responsive-smartphone-2026-09-25.md`
- ✅ Breakpoints unifiés (`≤599` mobile / `600–1024` tablette / `>1024` desktop) dans `style.css`, remplaçant 3 systèmes divergents
- ✅ Menu latéral : calque à 3 états (drawer plein écran hors-champ sur mobile, rail à icônes 64px replié par défaut sur tablette, ouvert sur desktop) — corrige le bug de marge morte mobile (64px réservés même menu fermé) et le bug d'overlay jamais affiché (sélecteur CSS cassé, préexistant)
- ✅ Tableaux larges (Positions, Investissements, positions ouvertes Trading) : `data-label` ajoutés (cartes mobiles lisibles), colonnes secondaires masquées sur tablette, panneau de détail généralisé (`static/js/row-detail-panel.js`, remplace `positions-detail-panel.js`)
- ✅ Page Trading : seuil de bascule colonne unique abaissé (1024→768px), hauteurs de graphique adaptatives, toolbar avec `flex-wrap` mobile, bouton de soumission collant
- ✅ Nouveau composant : barre de navigation basse mobile (`components/bottom-tab-bar.html`, Dashboard/Positions/Trading/Journal/Menu)
- 🟡 Non testé : orientation paysage téléphone (600-900px), appareil physique réel (harnais iframe fidèle aux media queries CSS mais pas à un vrai navigateur mobile)
- 🟡 Hors périmètre (pages non liées au menu depuis le 2026-09-21) : `spot_trading`/`futures_trading` débordent encore en tablette (~90-96px)
- ⏳ Geste tactile pour déplacer TP/SL sur le graphique Trading (Maj+glissé desktop, pas d'équivalent mobile) — décision produit en suspens, voir `decisions.md`

### À faire ⏳

#### Responsive (suite)
- 🟡 Portfolio chart du Dashboard : hauteur fixe (400px), pas revue dans le chantier du 2026-09-25 (pas identifiée comme cassée)
- 🟡 Débordement résiduel mineur (~23px) sur le tableau des positions ouvertes de Trading en tablette, même après masquage TP/SL

#### Futures Trading
- 🟡 Affichage du champ `strategy` dans la table futures_trading.html

#### Analytics/Journal
- 🟡 Django messages sur ces pages (actuellement seule investment l'affiche)

#### Vigil Integration (Phase 2 préparation)
- ✅ Bearer token / rate limiting Vigil / ingestion cron : répondus par la doc Vigil mise à jour le 2026-09-24, plus de question ouverte (les anciennes questions "monolithe vs granulaire" et "cache TTL" sont résolues de facto par l'implémentation du 2026-09-25 : un seul appel `/api/signals` par page, pas de cache Tradiaries nécessaire — voir `docs/plan-integration-vigil-2026-09-25.md`)
- 🔴 Vérifier chiffrement secrets API Vigil (crypto.cv, Binance, Etherscan) en base côté Vigil (hors périmètre Tradiaries, à confirmer avec l'équipe Vigil)
- 🟡 Cache Tradiaries à réenvisager en Phase 2 uniquement si le rate limit Vigil partagé (30/min, un seul token pour tous les utilisateurs Tradiaries) devient limitant avec plusieurs comptes actifs
- 🟡 Benchmark latency Render free : non prioritaire (Vigil lit désormais toujours en base, plus de fetch live à la requête)

#### Coach IA (relocalisé de Vigil, 2026-09-25)
- 🔴 Pas démarré — voir `docs/coach-ia-vers-tradiaries-2026-09-25.md` pour le cadrage repris (v1 = rule-checker déterministe, TDD sur le prompt, coaching conversationnel différé en v1.1/v2)
- ⏳ Questions à redébattre avant tout démarrage : choix du LLM de production, source de données prix/indicateurs historiques, accès direct BDD vs couche de service dédiée, pistes de différenciation non challengées (voir doc pour le détail)

#### `timeframe` texte libre vs liste prédéfinie (en suspens, 2026-09-25)
- ⏳ Décision non tranchée — voir `decisions.md`. Non bloquant pour le bandeau Vigil (filtrage v1 par ticker suivi + macro uniquement, pas par bucket temporel)

#### Déploiement
- 🟡 Test complet Render + Railway + Neon
- 🟡 Vérifications health checks watcher
- 🔴 Committer/merger le travail de la session (audit trail, migration `0017`/`0018`, tests renforcés, bandeau news Vigil) — rien n'est déployé tant que non mergé sur `prod`
- 🔴 Trancher l'inscription publique vs invite-only avant toute exposition non contrôlée (voir Problèmes connus / `decisions.md` en suspens)
- 🔴 Configurer `VIGIL_API_URL`/`VIGIL_BEARER_TOKEN` sur Render/Railway avant déploiement (absents en local, le bandeau reste simplement masqué sans ces variables — dégradation gracieuse déjà en place, pas bloquant mais la fonctionnalité restera invisible tant que non configurée)

---

## Statut de préparation production (2026-09-22)

**Verdict `/prod-check`** : 🟠 READY WITH WARNINGS pour Phase 1 (personnel) — 🔴 NOT READY pour ouverture à des utilisateurs non explicitement invités. Rapport complet : `docs/prod-check-2026-09-22.md`.

- Les 3 P0 de l'audit du 2026-09-10 (`docs/audit-production.md`) sont corrigés (machine d'états ordres, retry désactivé, verrou clôture atomique).
- Isolation multi-utilisateur vérifiée exhaustivement (grep sur tous les `views.py`) : aucune fuite trouvée.
- `check --deploy`, `makemigrations --check`, suite complète (85 tests) : tous propres.
- Bloquants restants : voir "Problèmes connus" ci-dessous (B1 travail non commité, B2 signup public).

## Problèmes connus

### Résolus cette session (2026-09-12)
- ✅ **Menu replié recouvrait le contenu** → Fixed avec `margin-left: calc(64px - 264px)`
- ✅ **Menu s'ouvrait après clique tabs** → Fixed avec localStorage initial setup sans animation
- ✅ **CSS désorganisé** → Refacto : layout global dans `style.css`, menu styling dans `side-menu.css`
- ✅ **Site blanc** → Fixed : import `style.css` dans tous les templates

### Trouvés cette session (2026-09-22, non corrigés)
- 🔴 **Inscription publique contredit le modèle "invite-only"** de la décision de sécurité Fernet — voir `decisions.md` en suspens et `docs/prod-check-2026-09-22.md`.
- 🟡 **`watch_tp_sl.py`** : un cycle réussi peut être mal classé "échec" sur console Windows (cp1252) à cause d'un caractère `✓` — sans impact prod (Railway = Linux/UTF-8). Voir `change-log.md` 2026-09-22 (TESTING).
- 🟡 Pas de protection anti-brute-force sur login/signup ; pas de monitoring/alerting (Sentry ou équivalent) — requis avant Phase 2, toujours absents.

### Résolus cette session (2026-09-25, refonte responsive)
- ✅ **Bande morte du menu mobile fermé** (64px réservés en permanence) → menu désormais un calque (jamais de push de contenu)
- ✅ **Zone grise 768px** (mode mobile appliqué au lieu de tablette) → breakpoints unifiés
- ✅ **Overlay du menu mobile jamais affiché** (bug préexistant, sélecteur CSS `body::before`/`.main-content::before` incohérent) → fusionné en une règle cohérente
- ✅ **Tableaux larges illisibles/débordants sur mobile et tablette** → `data-label` + colonnes masquées + panneau de détail
- ✅ **`position: fixed` menu mobile peut pas scrollable si beaucoup de liens** → non reproductible : `.side-menu` a déjà `overflow-y: auto`, vérifié suffisant pour les 8 liens actuels
- 🟡 **Graphique chart pas responsive en très petit (< 300px hauteur)** → partiellement adressé (hauteurs désormais adaptatives à la **largeur**, pas encore testé spécifiquement pour une hauteur d'écran très courte)

### Trouvés cette session (2026-09-25, non corrigés)
- 🟡 **Environnement dev local** : le process `runserver` a servi du contenu de template périmé à plusieurs reprises malgré `DEBUG=True` et des fichiers à jour sur disque (confirmé via un process séparé à chaque fois) — cause exacte non identifiée, mitigé en redémarrant le process. À surveiller lors de la prochaine session si ça persiste.
- 🟡 `apps/spot_trading`/`apps/futures_trading` (pages orphelines, plus liées depuis le menu) débordent encore en tablette (~90-96px) — hors périmètre du diagnostic initial (parcours utilisateur réel).

### En attente
- ❓ iOS Safari PWA install : valider sur appareil réel (PNG 192/512 en place, test requis)
- ❓ Refonte responsive : validation sur appareil physique/émulateur réel (le harnais de test utilisé le 2026-09-25 simule fidèlement les media queries CSS mais pas un vrai navigateur mobile — barre d'adresse, clavier virtuel, gestes tactiles)
- ❓ Refonte responsive : orientation paysage téléphone (600-900px) non testée

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
- [ ] Test PWA install sur iOS/Android réels
- [ ] HTTPS Render configuré + CSRF_TRUSTED_ORIGINS
- [ ] Railway : mêmes vars de sécurité que Render
- [ ] Neon DB : backup configuré
- [ ] Kraken API clé en ApiCredential (via page Settings)
- [ ] Watcher démarré sur Railway
- [ ] Health checks Render + Sentry logs
