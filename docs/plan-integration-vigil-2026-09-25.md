# Plan d'implémentation — Bandeau de news Vigil sur la page Trading

**Date** : 2026-09-25
**Décisions sources** : `.ai/decisions.md` → "Intégration des news Vigil — Bandeau contextuel sur la page Trading" (retenue), "Table/page dédiée aux news Vigil en v1" (rejetée).
**Hors périmètre** : Coach IA (aucune dépendance de code entre ce chantier et le Coach, seule l'API Vigil est partagée).

## 0. Vérification préalable — une hypothèse du Challenge est fausse

Le Challenge supposait un mapping nécessaire entre `symbol` Tradiaries (format paire exchange) et `ticker` Vigil (actif nu). Vérifié dans le code : `DEFAULT_TRADING_SYMBOLS` (`apps/live_trading/views.py`) et le champ `symbol` de `SpotTrading`/`FuturesTrading` stockent déjà des actifs nus (`'BTC'`, `'ETH'`, `'SOL'`...) — la conversion vers une paire Kraken (`resolve_pair()`) ne se fait qu'au moment d'appeler l'API Kraken, jamais en base. **Aucun mapping n'est donc nécessaire** : le filtrage `ticker in tracked_assets` fonctionne directement. Point à ne pas re-complexifier en implémentation.

## 1. Architecture

```
UserPreferences.tracked_assets (nouveau champ)
        ↓
apps/live_trading/views.py::vigil_signals_json()
        ↓ (1 seul appel, jamais par ticker)
apps/core/vigil_client.py::fetch_signals()  →  GET {VIGIL_API_URL}/signals (bearer token)
        ↓
filtrage Python : ticker in tracked_assets OR ticker is None (macro/géopolitique)
        ↓
JSON → bandeau JS (apps/live_trading/templates/live_trading/live_trading.html)
```

- Pas de persistance locale des signaux (pas de modèle `Signal` Tradiaries) : lecture à la demande à chaque chargement de la page Trading, cohérent avec la décision "pas de cache nécessaire pour protéger Vigil" (ingestion cron côté Vigil, lecture déjà instantanée).
- Un seul appel `/api/signals` sans paramètre `ticker` (récupère tout, filtrage ensuite côté Tradiaries) plutôt que `/api/signals/<source>` en boucle — résout de facto la question "monolithe vs granulaire" restée ouverte depuis le Challenge du 2026-09-24 : appeler par ticker suivi multiplierait les requêtes pour un gain nul (le filtrage se fait de toute façon en mémoire), et consommerait plus vite le budget de rate limit partagé (30/min pour tous les utilisateurs Tradiaries).
- Dégradation gracieuse obligatoire : Vigil down / timeout / bearer absent en dev → `fetch_signals()` retombe sur `[]`, la page Trading continue de fonctionner sans bandeau (même philosophie que `kraken_client.fetch_ohlc()` qui retombe sur `[]` si Kraken est indisponible).

## 2. Composants et dépendances

| Fichier | Nature | Dépend de |
|---|---|---|
| `config/settings.py` | + `VIGIL_API_URL`, `VIGIL_BEARER_TOKEN` (via `config()`, `default=''`) | — |
| `apps/core/vigil_client.py` | **Nouveau** — `fetch_signals(since=None)`, `check_health()` | `requests` (déjà en dépendance), settings ci-dessus |
| `apps/core/models.py::UserPreferences` | + champ `tracked_assets` (JSONField, liste de strings, `default=list`) | Migration `core.00XX` |
| `apps/dashboard/forms.py::UserStrategyForm` | + widget de sélection multiple sur `tracked_assets`, options = `DEFAULT_TRADING_SYMBOLS` (réutilisé depuis `apps/live_trading/views.py`, pas dupliqué) | — |
| `apps/dashboard/templates/dashboard/settings.html` | + section "Actifs suivis" dans le formulaire stratégie existant | — |
| `apps/live_trading/views.py` | + vue `vigil_signals_json()` | `vigil_client.fetch_signals`, `UserPreferences` |
| `apps/live_trading/urls.py` | + route `signals.json` | — |
| `apps/live_trading/templates/live_trading/live_trading.html` | + bandeau HTML/JS (fetch au chargement, rendu cards) | `static/css/trading.css` |
| `static/css/trading.css` | + styles bandeau (scroll horizontal natif `overflow-x:auto` + `scroll-snap`, pas de librairie JS) | — |

Aucune nouvelle dépendance Python/JS externe.

## 3. Missions (ordre d'exécution)

### Mission 1 — Client Vigil + configuration (fondation)
- `apps/core/vigil_client.py` : `fetch_signals(since=None)` → GET `/api/signals`, header `Authorization: Bearer <VIGIL_BEARER_TOKEN>`, timeout court (ex. 5s, cohérent avec les appels Kraken existants), gestion 401/429/timeout/JSON invalide → retour `[]` + log warning (jamais d'exception qui remonte à la vue).
- `check_health()` optionnel (GET `/api/health`, pas de bearer requis) — utile pour un futur indicateur d'état, pas strictement nécessaire pour le bandeau v1 ; à garder en option basse priorité.
- Variables d'environnement `VIGIL_API_URL`/`VIGIL_BEARER_TOKEN` : ne pas lever de `RuntimeError` si absentes (contrairement à `API_CREDENTIAL_ENCRYPTION_KEY`) — Vigil est une donnée d'agrément, pas un prérequis de sécurité/fonctionnement du cœur de l'app.

### Mission 2 — Actifs suivis (préférences utilisateur)
- Migration : `UserPreferences.tracked_assets` (JSONField, `default=list`, `blank=True`).
- `UserStrategyForm` : widget multi-select (checkboxes ou `<select multiple>`) sur `DEFAULT_TRADING_SYMBOLS`.
- `settings_view`/`save_strategy` (déjà existants) : aucun changement de logique, le `ModelForm` gère le nouveau champ automatiquement.

### Mission 3 — Endpoint JSON de signaux filtrés
- `vigil_signals_json(request)` : récupère `tracked_assets` de `request.user` (liste vide par défaut → seuls les signaux macro `ticker=None` s'affichent), appelle `vigil_client.fetch_signals()`, filtre `ticker in tracked_assets or ticker is None`, renvoie uniquement les champs nécessaires à l'affichage neutre (`source`, `ticker`, `summary`, `timestamp`, `reliability_tier`) — **ne pas renvoyer `raw_payload`/`news_score` bruts au template** pour ne pas tenter d'en faire un affichage scoré/coloré plus tard sans repasser par une décision explicite.

### Mission 4 — Bandeau UI sur la page Trading
- Cards : résumé (`summary`) + source + badge fiabilité neutre (texte "Fait vérifié" / "Donnée quantitative" / "Analyse" selon `reliability_tier`, pas de couleur rouge/vert directionnelle).
- Scroll horizontal **manuel uniquement** (CSS `overflow-x: auto; scroll-snap-type: x mandatory`, pas de `setInterval`/auto-play JS).
- Aucun élément cliquable menant à une action de trade (pas de lien "Acheter"/"Vendre" sur une card).
- Placement : au-dessus du graphique existant, dans `live_trading.html`.

### Mission 5 — Tests (palier Standard, cohérent avec la décision "Amélioration du testing" du 2026-09-22)
- `VigilClientTests` (`apps/core/tests.py`) : mock `requests.get` (haut niveau, comme pour `kraken_client`) — succès, 401, 429, timeout, JSON invalide → chaque cas retourne `[]` sans exception.
- Tests `UserPreferences.tracked_assets` : sauvegarde/lecture via `UserStrategyForm`, isolation multi-utilisateur (pattern `MultiUserIsolationTests` déjà en place).
- `VigilSignalsJsonViewTests` (`apps/live_trading/tests.py`) : mock `vigil_client.fetch_signals` (jamais `requests` directement) — filtrage correct (actifs suivis + `ticker=None` toujours inclus, actifs non suivis exclus), réponse vide si Vigil down.
- **Non couvert par les tests automatisés** (comme le drag & drop TP/SL) : rendu visuel du scroll horizontal — vérification manuelle navigateur requise avant de considérer la mission terminée.

## 4. Décisions en suspens à signaler (ne pas planifier autour)

- **Format exact de `tracked_assets`** : ce plan part sur un `JSONField` (liste de strings), le plus simple et cohérent avec l'absence de modèle `Asset` dédié dans le projet. Ce n'est pas un point gelé explicitement en `/gel-decision` — si un modèle relationnel est préféré (ex. table `TrackedAsset(user, symbol)` pour bénéficier de contraintes DB), le dire avant la Mission 2, la migration change.
- **`timeframe` texte libre vs liste prédéfinie** : confirmé hors périmètre (`.ai/decisions.md`, en suspens) — ce plan n'en dépend pas, le filtrage v1 est uniquement par ticker suivi + macro, pas par bucket temporel.
- **Mise à jour de `project-context.md`/`change-log.md`** : les 4 points listés le 2026-09-24 comme "à trancher via `/gel-decision`" (bearer token, rate limit, cache TTL, monolithe vs granulaire) sont maintenant tous répondus (par la doc Vigil mise à jour et par ce plan) — ces entrées sont obsolètes et devraient être nettoyées en session-end, pas un blocage pour démarrer l'implémentation.

Prêt pour `/implementation` sur ces 5 missions, dans l'ordre.
