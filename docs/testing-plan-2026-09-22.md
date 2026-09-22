# Plan d'implémentation — Renforcement du testing (2026-09-22)

**Découle de** : `.ai/decisions.md` → "Amélioration du testing — nouveaux tests + intégration BDD/API (2026-09-22)"
**Palier de rigueur** : Standard (`.ai/project-rules.md`) → tests unitaires + tests d'intégration attendus, pas d'e2e navigateur requis pour ce chantier.
**Décision liée écartée** : ordres futures LIVE — hors périmètre (voir `decisions.md`, rejetée). Aucun test futures LIVE dans ce plan.
**Décision en suspens vérifiée** : la seule décision en suspens du projet (clé Fernet per-user / vault) ne bloque rien ici — indépendante du testing.

## Architecture / convention de test retenue

- Toujours `django.test.TestCase` (BDD réelle SQLite, transaction rollback par test) — pas de nouvelle dépendance.
- Mocks **haut niveau uniquement**, au sens décidé : on mocke la fonction appelée par le code testé, jamais `requests`/`_sign()` directement.
  - Pour tester la logique de `trading_service.py` : mock `kraken_client.add_spot_order` / `fetch_current_price` (déjà la pratique actuelle).
  - Pour tester `kraken_client.py` lui-même (Mission 2) : le "haut niveau" pertinent est **`_private_request`/`_public_request`** — ce sont les seules fonctions encapsulant HTTP/signature. Aucun test ne doit mocker `requests.Session` ou `_sign()` directement (explicitement écarté en décision).
- Un fichier de test par app existante (`apps/core/tests.py`, `apps/dashboard/tests.py`) — pas de nouveau module de test à créer sauf Mission 1 (commande de management, voir ci-dessous).

## Missions (par ordre de priorité)

### Mission 1 — Watcher `watch_tp_sl.py` (priorité haute)
**Pourquoi en premier** : c'est le composant qui clôture des positions LIVE réelles sans supervision humaine directe (process Railway) ; c'est aussi le seul des 4 sans aucune couverture actuelle, même indirecte.

Fichier : nouveau `apps/core/tests_watcher.py` (ou classe dédiée ajoutée à `tests.py` si le projet préfère un seul fichier — à trancher en implémentation selon la taille).

Cas à couvrir :
- `--once` exécute un seul cycle et retourne (pas de boucle infinie dans le test).
- Un cycle réussi (mock `check_tp_sl` retournant une liste d'events) appelle `touch_watcher_heartbeat()`.
- Un cycle qui lève une exception dans `check_tp_sl` (mock avec `side_effect`) : la commande ne crashe pas, log l'erreur, et **n'appelle pas** `touch_watcher_heartbeat()` (invariant documenté dans le code : "heartbeat non mis à jour si échec").
- `--interval` personnalisé est bien lu depuis les options (pas nécessairement testé via un vrai `sleep` — vérifier que `options['interval']` est utilisé, ou mocker `time.sleep` pour vérifier l'argument passé).

Dépendances : aucune — `check_tp_sl` et `touch_watcher_heartbeat` sont déjà mockables tels quels.

### Mission 2 — `kraken_client.py` (priorité haute)
**Pourquoi** : zone qui manipule des secrets et déclenche des ordres réels ; actuellement seulement testée indirectement (le mock sur `add_spot_order` dans `trading_service` masque totalement son contenu).

Fichier : nouvelle classe dans `apps/core/tests.py` (ex. `KrakenClientTests`), à côté de `KrakenOhlcTests` existant.

Cas à couvrir, en mockant `_private_request` (et `_public_request` pour `resolve_pair` si nécessaire) :
- `add_spot_order` : construit le bon payload (`pair` résolu, `volume` quantifié à 8 décimales, `type`, `ordertype`), refuse un `side` invalide, exige un `price` si `ordertype='limit'`, transmet `validate`/`userref` seulement si fournis, lève `KrakenAPIError` si aucun `txid` retourné hors validate.
- `query_orders` : retourne `{}` sans appel réseau si `txids` vide ; sinon joint bien les txids en CSV.
- `fetch_order_fill_price` : retourne `None` si l'ordre n'est pas `closed` ou absent ; retourne le `Decimal(price)` sinon.
- `cancel_order` : appelle `_private_request` avec le bon txid, en `retryable=False`.
- `_private_request` (test direct, en mockant `_get_kraken_credentials` et `_http_session`/le `.post` retourné) : lève `KrakenAPIError` si clés absentes ; lève `KrakenAPIError` si Kraken renvoie `error` non vide ; lève `KrakenAPIError` sur JSON invalide.

### Mission 3 — `portfolio_service.py` (priorité moyenne)
**Pourquoi** : "cœur des calculs" (project-context.md) sans classe de test dédiée ; risque silencieux si une régression fausse les stats affichées au dashboard.

Fichier : nouvelle classe `PortfolioServiceTests` dans `apps/core/tests.py`.

Cas à couvrir (au minimum, un test par fonction publique) :
- `compute_investment_stats` / `compute_spot_stats` / `compute_futures_stats` : cas vide (aucune donnée → stats à zéro/`None`, pas d'exception) + cas avec données, filtré par `trade_mode`.
- `compute_global_stats` : agrège correctement les trois catégories.
- `compute_futures_analytics` : ventilation par stratégie/symbole/ressenti/direction — au moins un test vérifiant que `_breakdown_by` regroupe correctement.
- `build_chart_series` : série cumulée croissante/décroissante cohérente avec les événements (`_cumulative_series`).
- Isolation multi-utilisateur : chaque fonction ne doit renvoyer que les données du `user` passé (test rapide avec deux users, données croisées).

### Mission 4 — `apps/dashboard/views.py` (priorité moyenne, car modifié dans le diff en cours)
**Pourquoi** : seulement 2 tests existants alors que le fichier fait partie du diff non commité actuel (`M apps/dashboard/views.py`) — risque de régression non couverte sur du code qui vient de bouger.

Fichier : extension de `apps/dashboard/tests.py`.

Cas à couvrir :
- `dashboard()` : rendu correct authentifié, redirect si non authentifié.
- `settings_view` / `save_strategy` : sauvegarde bien `UserPreferences.strategy` pour le bon user (isolation).
- `create_api_credential` / `delete_api_credential` : création/suppression scoped à `request.user`, refus si tentative sur une credential d'un autre user (404, pas 403 — cohérent avec le pattern IDOR déjà en place ailleurs).
- `signup` : création de compte + connexion automatique (déjà mentionné comme fonctionnalité en place, à vérifier si déjà testé ailleurs pour ne pas dupliquer).

## Hors périmètre de ce plan
- Tout test lié aux ordres futures LIVE (décision rejetée).
- Tests e2e navigateur (Playwright/Selenium) — non requis au palier Standard pour ce chantier ; le plan `/run` existant sert déjà à la vérification manuelle UI.
- Mocks bas niveau sur `requests`/`_sign()` (décision explicite : haut niveau seulement).

## Critère de sortie
- `python manage.py test apps.core apps.dashboard` toujours vert après chaque mission.
- Mise à jour de `change-log.md` à chaque mission complétée (via `/implementation`), pas seulement à la fin.
- `project-context.md` : mettre à jour le compteur de tests ("43 tests ✅" actuellement) une fois les 4 missions terminées.
