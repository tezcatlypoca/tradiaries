# Audit de préparation à la production

**Date :** 2026-09-10  
**Périmètre :** sécurité, observabilité, robustesse et gestion des échecs  
**Verdict :** **NO-GO pour le trading LIVE**, **GO conditionnel pour un staging privé en PAPER**

## Synthèse exécutive

Le projet possède de bonnes fondations : authentification sur les vues métier, formulaires Django, protection CSRF, secrets API chiffrés avec une clé dédiée obligatoire en production, timeouts réseau, health checks, heartbeat du watcher, sauvegarde PostgreSQL documentée, dépendances figées et service systemd durci.

La production avec ordres réels reste bloquée par le protocole d'exécution Kraken. Un ordre externe peut être exécuté sans être persisté localement, les requêtes privées `POST` sont automatiquement rejouées sur certains échecs HTTP, et deux instances peuvent tenter de clôturer la même position. Cela peut produire une position inconnue de l'application, un résultat d'ordre ambigu ou une double clôture.

Le modèle d'autorisation est également « tout utilisateur authentifié voit et modifie tout ». Cela n'est acceptable que si l'instance est explicitement mono-utilisateur et que la création des comptes est strictement contrôlée.

## État vérifié

Contrôles exécutés avec l'environnement virtuel du projet :

| Contrôle | Résultat |
|---|---|
| `manage.py check --deploy` avec configuration HTTPS de production simulée | OK, aucun avertissement |
| `manage.py makemigrations --check --dry-run` | OK, aucun changement |
| `manage.py test` en configuration de test normale | OK, 16 tests |
| `python -m pip check` | OK |
| `env.txt` | Présent localement, ignoré par Git, non suivi, aucun historique Git détecté |

Exécuter les tests avec `SECURE_SSL_REDIRECT=True` sans envoyer de requêtes HTTPS produit cinq réponses `301`. Ce n'est pas une régression applicative : la CI doit séparer les tests ordinaires du contrôle de configuration production.

## Bloquants avant activation du LIVE

### P0-1 — Ordre Kraken exécuté avant persistance locale

**Preuve :** [`apps/core/trading_service.py`](../apps/core/trading_service.py) appelle `add_spot_order()`, attend éventuellement le prix d'exécution, puis crée seulement ensuite le modèle `SpotTrading`.

**Scénarios d'échec :**

- Kraken accepte l'ordre, puis le processus web tombe avant `objects.create()` ;
- `fetch_order_fill_price()` ou le fallback de prix lève une erreur après l'achat ;
- l'écriture PostgreSQL échoue après l'exécution distante ;
- le navigateur réessaie une requête dont le résultat précédent est inconnu.

**Impact :** ordre réel absent de la base, portefeuille et watcher incohérents, intervention manuelle nécessaire.

**Action requise :** implémenter une machine d'état persistée (`PENDING`, `SUBMITTED`, `OPEN`, `CLOSING`, `CLOSED`, `FAILED`, `RECONCILE_REQUIRED`) avec un identifiant client unique créé avant l'appel externe. Réconcilier systématiquement les états ambigus avec Kraken. Une transaction SQL seule ne peut pas rendre atomiques PostgreSQL et Kraken.

### P0-2 — Retry automatique des `POST` privés Kraken

**Preuve :** [`apps/core/kraken_client.py`](../apps/core/kraken_client.py) configure `urllib3.Retry` avec `POST` dans `allowed_methods` et l'utilise notamment pour `AddOrder` et `CancelOrder`.

**Impact :** après un `429`/`5xx` ou une rupture de connexion, le client ne peut pas savoir si Kraken a traité l'ordre. Le rejeu automatique transforme cet état ambigu en risque financier. Le nonce milliseconde peut aussi entrer en collision entre appels concurrents.

**Action requise :** ne jamais rejouer aveuglément une commande non idempotente. Séparer les sessions lecture/commande, générer des nonces monotones entre processus et utiliser un identifiant client Kraken (`userref` ou équivalent supporté) pour rechercher puis réconcilier l'ordre avant toute nouvelle tentative.

### P0-3 — Clôture TP/SL concurrente non verrouillée

**Preuve :** [`apps/core/trading_service.py`](../apps/core/trading_service.py) charge les positions ouvertes, teste `exit_price`, envoie l'ordre de vente, puis sauvegarde. Il n'y a ni état `CLOSING`, ni verrou distribué, ni revendication atomique de la position.

**Impact :** deux watchers, ou un clic manuel pendant un cycle, peuvent vendre deux fois la même quantité. `select_for_update()` seul ne suffit pas si le verrou est conservé pendant l'appel réseau.

**Action requise :** garantir une seule instance active du watcher et revendiquer atomiquement la position (`OPEN` vers `CLOSING`) avant l'appel externe. Ajouter des tests concurrents PostgreSQL.

## Sécurité

### P1 — Autorisation globale, sans propriétaire ni rôle métier

Toutes les vues métier utilisent `login_required`, ce qui est positif. En revanche, les modèles n'ont aucun propriétaire et les requêtes utilisent `objects.all()` ou une clé primaire globale. Tout compte authentifié peut consulter, modifier ou supprimer tous les trades et toutes les clés API, et déclencher un ordre LIVE.

**Décision requise :**

- instance mono-utilisateur : désactiver toute inscription publique, limiter la création de comptes à l'administration, documenter cette contrainte et réserver paramètres/LIVE à un groupe explicite ;
- instance multi-utilisateur : ajouter un propriétaire, filtrer chaque queryset et appliquer des permissions objet. Les clés API doivent être rattachées à leur propriétaire.

### P1 — Configuration HTTPS sûre seulement si l'exploitation la fournit

[`config/settings.py`](../config/settings.py) lit correctement `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, cookies sécurisés, redirection TLS, HSTS et proxy TLS depuis l'environnement. Les valeurs par défaut restent adaptées au développement et non à Internet.

`DEBUG=False` impose une longue `SECRET_KEY` et une clé Fernet dédiée, mais ne refuse pas un démarrage sans cookies sécurisés ni redirection TLS. Une erreur de variables d'environnement peut donc laisser démarrer une configuration insuffisante.

**Action requise :** rendre les réglages HTTPS obligatoires dans un profil production. Valider le proxy avant HSTS, puis activer progressivement HSTS. Exécuter `check --deploy` dans la CI avec les variables de production attendues.

### P1 — Gestion des clés API à renforcer

Points positifs : chiffrement Fernet, clé dédiée obligatoire avec `DEBUG=False`, formulaire sans réaffichage du secret et administration en lecture seule.

Risques restants :

- [`apps/core/crypto.py`](../apps/core/crypto.py) transforme un `InvalidToken` en chaîne vide sans log ni alerte ; une rotation ou corruption ressemble à une clé absente ;
- plusieurs clés Kraken sont autorisées, mais [`apps/core/kraken_client.py`](../apps/core/kraken_client.py) choisit silencieusement la première ;
- aucune date de rotation, révocation, dernière utilisation ou trace de l'utilisateur ayant modifié une clé ;
- les permissions Kraken minimales ne sont pas suffisamment explicites pour le LIVE : retrait de fonds interdit, trading uniquement, restriction IP si disponible.

**Action requise :** imposer une seule clé active par plateforme et propriétaire, faire échouer explicitement le déchiffrement, journaliser les changements sans secret et documenter/tester la rotation de `API_CREDENTIAL_ENCRYPTION_KEY`.

### P2 — Durcissement HTTP et sessions incomplet

`SecurityMiddleware`, CSRF et `XFrameOptionsMiddleware` sont actifs. Il reste à définir une politique de session, une politique CSP, `Referrer-Policy` et `Permissions-Policy` au reverse proxy ou dans Django. Tester réellement CSRF, login, logout, brute force et permissions ; les tests actuels utilisent `force_login()` et ne couvrent pas ces frontières.

### P2 — Secrets et artefacts locaux

`env.txt`, `.env`, la base SQLite et `docs/` sont ignorés. `env.txt` contient des variables PostgreSQL sensibles, mais l'audit n'a trouvé ni suivi Git ni historique Git pour ce fichier. Faire néanmoins tourner le mot de passe si le poste, une sauvegarde ou une ancienne copie a été exposé.

Le fait d'ignorer tout `docs/` et `.github/` empêche de versionner ce rapport, la documentation d'exploitation et une CI GitHub. Remplacer ces règles globales par des exclusions ciblées des exports sensibles.

## Observabilité

### P1 — Pas de corrélation ni de journal d'audit des ordres

Les logs texte incluent endpoint, paire, sens, volume et `txid`, mais pas d'identifiant de requête, d'utilisateur, de position locale, de durée, de tentative ou d'état de réconciliation. Ils ne permettent pas de reconstituer sûrement le cycle de vie d'un ordre.

**Action requise :** produire des logs structurés JSON avec `request_id`, utilisateur, `trade_id`, identifiant client, `txid`, opération, latence, résultat et transition d'état. Ne jamais loguer clé, signature, passphrase, payload d'authentification ou URL de base contenant un mot de passe. Définir rétention, accès et rotation.

### P1 — Alertes indispensables absentes

Le projet n'intègre ni suivi d'exceptions ni métriques ni canal d'alerte. Les événements suivants doivent alerter immédiatement :

- ordre soumis avec résultat inconnu ou réconciliation échouée ;
- position bloquée en `PENDING`/`CLOSING` ;
- watcher absent ou cycle en échec ;
- erreurs Kraken répétées, nonce invalide ou rate limit ;
- échec de sauvegarde/restauration ;
- erreur de déchiffrement d'une clé ;
- taux de réponses 5xx ou latence anormale.

Sentry/OpenTelemetry et Prometheus sont adaptés, mais le besoin prioritaire est un mécanisme d'alerte testé de bout en bout.

### P1 — Heartbeat trompeur pendant un cycle

[`apps/core/management/commands/watch_tp_sl.py`](../apps/core/management/commands/watch_tp_sl.py) écrit le heartbeat avant puis après `check_tp_sl()`. Si le cycle échoue, systemd redémarre le processus, ce qui est correct. En revanche, le premier heartbeat peut annoncer « running » avant qu'un cycle réussi ait eu lieu.

**Action requise :** exposer séparément `process_alive`, `last_cycle_started`, `last_cycle_succeeded`, durée, nombre de positions contrôlées/fermées et dernière erreur. Le check du watcher doit rester un check de fraîcheur et alimenter une alerte.

### P2 — Health checks utiles mais minimaux

[`apps/investment/views.py`](../apps/investment/views.py) vérifie la connexion DB et renvoie un JSON sans détail interne, ce qui convient pour une readiness simple. Il manque un liveness indépendant de la DB, un timeout PostgreSQL explicite et des métriques. Ne pas ajouter Kraken au health check web principal : une panne fournisseur ne doit pas provoquer une boucle de redémarrage.

### P2 — Sauvegardes non observées

[`deploy/backup-postgres.sh`](../deploy/backup-postgres.sh) utilise `set -euo pipefail`, crée un dump custom et un checksum, puis applique une rétention. C'est une bonne base. Le checksum ne protège pas contre une modification malveillante s'il est stocké avec le dump, et aucun succès de restauration n'est automatisé ni supervisé.

**Action requise :** chiffrement, copie hors hôte/compte, alerte sur absence de backup, restauration périodique automatisée et objectifs RPO/RTO mesurés.

## Robustesse et gestion des échecs

### P1 — Exceptions post-exécution incomplètement maîtrisées

La vue LIVE ne capture que `TradingError`. Après un `AddOrder` réussi, `fetch_order_fill_price()` peut lever `KrakenAPIError`, et `objects.create()` peut lever une erreur de base. Ces exceptions donnent une 500 tout en laissant potentiellement un ordre réel actif. Le même problème existe à la clôture : la récupération du fill n'est pas protégée par le `try` qui entoure l'envoi.

**Action requise :** traiter explicitement chaque phase et persister les états ambigus. Ne pas convertir aveuglément toute exception en succès ou échec ; après soumission, la bonne réponse est souvent « à réconcilier ».

### P1 — Modèle de position insuffisant pour l'exécution réelle

Une position est considérée fermée dès que `exit_price` est renseigné. Le modèle ne conserve pas statut d'ordre, quantité exécutée, frais, devise de cotation, exécutions partielles, timestamps d'envoi/fill, cause d'échec ou identifiant client. `exit_price_2` suppose implicitement deux sorties de taille égale.

**Action requise :** séparer position, ordre et exécution (`Position`, `Order`, `Fill`) avant d'étendre le LIVE. Calculer PnL net avec frais et quantités exécutées ; formaliser les sorties partielles.

### P1 — Watcher monolithique et reprise grossière

Une exception inattendue sur une position termine toute la commande ; systemd redémarre après 10 secondes. Il n'y a ni isolation par position, ni backoff global, ni limite de cycles en erreur, ni arrêt spécifique sur erreur d'authentification. Le polling séquentiel effectue potentiellement de nombreux appels Kraken et peut dépasser l'intervalle configuré.

**Action requise :** isoler et mesurer les erreurs par position sans masquer les erreurs systémiques, appliquer backoff/jitter, empêcher le chevauchement des cycles et utiliser une récupération de prix groupée ou un flux adapté.

### P2 — Base de données sans délais ni politique de connexions

La configuration PostgreSQL transmet les options de l'URL, mais ne fixe pas par défaut `connect_timeout`, `statement_timeout` ni `CONN_MAX_AGE`. Une panne réseau ou requête bloquée peut immobiliser un worker web ou le watcher.

**Action requise :** définir des délais adaptés dans `DATABASE_URL`/`OPTIONS`, dimensionner le pool avec Gunicorn/PostgreSQL et tester perte/reprise de connexion.

### P2 — Dépendances externes dans les requêtes web

Les pages de portefeuille récupèrent des prix Kraken pendant le rendu. Les timeouts et le cache de 60 secondes limitent le risque mais plusieurs symboles sont interrogés séquentiellement, jusqu'à deux paires chacun. Une dégradation Kraken augmente donc directement la latence utilisateur.

**Action requise :** stocker le dernier prix connu avec son timestamp, rafraîchir hors requête et afficher explicitement l'âge/la qualité de la donnée. Ne pas utiliser un niveau TP/SL comme prix d'exécution de repli pour un ordre LIVE non confirmé.

### P2 — Couverture de tests insuffisante sur les risques financiers

Les 16 tests couvrent quelques validations, le PnL, PAPER, le déclenchement TP et les health checks. Ils ne couvrent pas :

- succès/timeout/`5xx`/réponse invalide avant et après acceptation d'un ordre ;
- idempotence et réconciliation Kraken ;
- concurrence clic manuel/watcher/deux watchers ;
- permissions et isolation utilisateur ;
- CRUD des clés, chiffrement invalide et rotation ;
- CSRF et méthodes HTTP ;
- sauvegarde/restauration ;
- exécution réelle sous PostgreSQL.

Ajouter des tests unitaires du protocole d'ordre, des tests d'intégration PostgreSQL avec concurrence et un environnement Kraken de validation sans fonds. Les tests financiers doivent vérifier les invariants, pas seulement les codes HTTP.

## Contrôles déjà satisfaisants

- Toutes les vues métier recensées sont protégées par authentification.
- Les mutations utilisent `POST` et conservent la protection CSRF Django.
- Les entrées courantes passent par des formulaires Django avec normalisation et validation de valeurs positives/TP/SL.
- Les clés API sont chiffrées en base ; une clé Fernet séparée est obligatoire lorsque `DEBUG=False`.
- Les appels Kraken ont des timeouts ; les appels de lecture bénéficient de retries et cache.
- `external_ref` est unique pour les trades importés/enregistrés.
- Les dépendances sont épinglées et Gunicorn/PostgreSQL sont déclarés.
- Le service watcher utilise un compte dédié, `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem` et une zone d'écriture limitée.
- Les endpoints `/healthz/` et `/healthz/watcher/` ne divulguent pas d'exception interne.
- Le script de sauvegarde échoue immédiatement en cas d'erreur et documente une restauration manuelle.

## Plan de remédiation priorisé

### Avant toute transaction LIVE

1. Concevoir et migrer la machine d'état `Order`/`Fill` avec identifiant client et réconciliation.
2. Retirer les retries aveugles sur les commandes Kraken et fiabiliser les nonces.
3. Sérialiser les clôtures par revendication atomique et garantir un watcher unique.
4. Ajouter les tests d'échecs ambigus et de concurrence sous PostgreSQL.
5. Restreindre l'accès LIVE et aux clés API à un rôle explicite.

### Avant exposition Internet

1. Figer le mode mono-utilisateur ou implémenter la propriété des objets.
2. Rendre le profil HTTPS obligatoire et tester le reverse proxy réel.
3. Installer logs structurés, suivi d'exceptions, métriques et alertes.
4. Configurer délais PostgreSQL, serveur Gunicorn, `collectstatic` et limites de ressources.
5. Versionner une CI et la documentation non sensible ; scanner les secrets et dépendances.

### Avant le GO production

1. Déployer en staging avec une clé Kraken sans retrait et des montants plafonnés.
2. Tester coupures réseau, `429`/`5xx`, crash après soumission, double clic et deux watchers.
3. Tester backup chiffré, restauration isolée et rotation des secrets.
4. Vérifier tableaux de bord et alertes par injection d'incidents.
5. Documenter arrêt d'urgence, désactivation du LIVE, réconciliation manuelle et contacts d'incident.

## Critères de GO/NO-GO

Le GO LIVE exige au minimum : zéro ordre non réconciliable lors des tests de panne, impossibilité démontrée d'une double clôture, permissions explicites, alertes opérationnelles testées, restauration validée et procédure d'urgence répétée.

Tant que les trois constats P0 ne sont pas corrigés et testés, conserver `trade_mode=PAPER` et retirer ou désactiver côté serveur la possibilité d'envoyer des ordres LIVE.
