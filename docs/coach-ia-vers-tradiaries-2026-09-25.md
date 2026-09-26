# Coach IA — dossier de transfert vers Tradiaries (2026-09-25)

> Ce document résume le cadrage du Coach IA fait côté Vigil le 2026-09-25, avant la décision de le déplacer vers Tradiaries. Il est destiné à être discuté avec l'agent/l'équipe qui travaille sur Tradiaries, pour reprendre ce cadrage dans son nouveau contexte plutôt que de repartir de zéro. Voir `.ai/decisions.md` (Vigil) pour la décision de relocalisation elle-même et ses raisons.

## Pourquoi le Coach IA n'est plus prévu dans Vigil

Le cadrage initial du 2026-09-25 prévoyait le Coach comme un module Python dans le repo Vigil. Reconsidéré le même jour :

- **Duplication de connecteurs évitée** : le rule-checker du Coach a besoin de données historiques de marché (prix/indicateurs autour d'un trade passé). Tradiaries aura de toute façon besoin de connecteurs d'API d'exchange pour ses propres fonctionnalités — les dupliquer dans Vigil aurait été redondant.
- **Accès natif à la BDD utilisateur** : le Coach a besoin du journal de trades et des règles de stratégie de l'utilisateur, qui vivent dans la BDD Tradiaries (app Django multi-user). Héberger le Coach dans Tradiaries lui donne un accès direct, sans construire de flux de synchronisation inter-services Vigil↔Tradiaries — point qui restait explicitement non tranché dans le cadrage initial.
- **Les news restent accessibles sans rien changer côté Vigil** : Tradiaries peut consommer les signaux déjà scorés par Vigil (`importance`/`novelty`/`source_count`, buckets timeframe) via l'API HTTP existante (`/api/signals`, `/api/signals/<source>`), déjà sécurisée par bearer token + rate limiting et déjà documentée (`docs/API_DOCUMENTATION.md`). Aucune route Vigil supplémentaire n'est nécessaire a priori pour ce cas d'usage.

Vigil garde donc son rôle actuel : fournisseur de données et de signaux scorés, consommé via API. Il n'héberge plus aucun code, prompt système ni harnais de test lié au Coach.

## Ce qui était déjà cadré (repris tel quel comme point de départ)

### Méthodologie
Tests de comportement du prompt système écrits **avant** le prompt lui-même (TDD appliqué au prompt engineering), puis itération du prompt jusqu'à convergence sur le jeu de tests.

### Périmètre fonctionnel v1
- v1 = **rule-checker déterministe seul** : comparaison factuelle entre un trade du journal et une règle de stratégie documentée par l'utilisateur. Sortie = constat de violation / non-violation, rien de plus.
- Le coaching ouvert de résilience/discipline (dialogue libre pour aider l'utilisateur à mieux suivre sa stratégie) est explicitement **différé en v1.1/v2**. Raison du non-bundling avec le rule-checker : la partie conversationnelle ouverte est bien plus difficile à borner et à tester, et fait courir à toute la livraison v1 le risque de dérive vers du conseil financier déguisé — identifié comme le risque principal du Coach.
- Différenciation ciblée retenue : le rule-checker doit s'appuyer sur les signaux déjà scorés par Vigil, pas seulement sur le journal utilisateur seul — sans quoi il n'est pas différencié de l'offre existante chez des concurrents identifiés (TraderSync/Cypher, TradesViz), qui font déjà de la détection de violation de règle par IA sur le seul journal de trade.

### Jeu de tests de comportement du prompt
- Couvre obligatoirement deux types d'échec, dès la conception :
  - **Sous-refus** : dérive vers un conseil financier déguisé.
  - **Sur-refus** : coach qui refuse même une explication neutre déjà couverte par les données Vigil.
- Cas de test explicitement requis : distinguer « violation de règle » de « mauvais résultat ». Un trade qui suit la règle mais perd n'est **pas** une violation ; un trade qui l'enfreint mais gagne **en est** une. Le P&L ne doit jamais influencer le jugement de conformité à la règle.
- Prompts de test adverses (contournement, insistance, reformulation, ambiguïté) inclus dès la conception du jeu de tests, pas ajoutés après coup.
- Mécanique v1 : règles déterministes. Un blocklist seul (mots-clés/patterns bannis) ne couvre que le sous-refus ; chaque cas de test de sur-refus doit en plus porter une assertion positive (« la réponse doit mentionner X/Y ») pour être réellement couvert dès la v1, sans attendre un juge LLM.
- v2 : ajout d'un juge LLM en complément du déterministe (pas en remplacement), pour couvrir les dérives plus subtiles.

## Questions à redébattre dans le contexte Tradiaries

Ces points étaient en suspens côté Vigil ; certains se résolvent d'eux-mêmes avec la relocalisation, d'autres doivent être reformulés dans le contexte Tradiaries (app Django multi-user, accès natif BDD) plutôt que repris tels quels :

1. **Choix du modèle LLM de production.** Les benchmarks généraux consultés côté Vigil (AgentHarm, robustesse au system prompt) favorisaient nettement les modèles fermés (Claude, GPT) sur la résistance à la pression adverse par rapport à un modèle ouvert type Mistral self-hosté, à scaffold égal. Mais aucun benchmark généraliste ne teste la frontière spécifique « coach vs conseiller financier » propre à ce projet : le harnais de tests (une fois construit côté Tradiaries) reste l'instrument de décision final ; les benchmarks généraux ne servent qu'à présélectionner des candidats. Sous-question : si un modèle open-weight est malgré tout retenu, un filtre de sortie déterministe en production (pas seulement en test/CI, réutilisant les règles du harnais) est probablement nécessaire pour compenser l'écart d'alignement mesuré.
2. **Source de données historiques prix/indicateurs pour le rule-checker.** La direction générale (reconnecter une API d'exchange) était actée côté Vigil, mais pas l'exchange/API précis. À trancher côté Tradiaries — potentiellement mutualisé avec d'autres besoins de données de marché de Tradiaries plutôt que choisi uniquement pour le Coach.
3. **Flux de données journal de trade + stratégie.** Ce point disparaît quasiment tel quel : avec le Coach hébergé dans Tradiaries, l'accès au journal de trades et aux règles de stratégie devient un accès BDD interne, pas un flux inter-services à construire. À vérifier néanmoins : le Coach doit-il lire directement les tables Django, ou passer par une couche de service dédiée (pour ne pas coupler le prompt engineering au schéma ORM directement) ?
4. **Accès aux news/signaux Vigil.** À vérifier côté Tradiaries : le contrat de fraîcheur des données Vigil (ingestion planifiée par cron, pas de fetch live à la requête — voir `docs/API_DOCUMENTATION.md`, section fraîcheur) est-il compatible avec la cadence d'inférence attendue du Coach ? Le rate limiting server-side de Vigil (`VIGIL_RATE_LIMIT_PER_MINUTE`) est-il suffisant pour le volume d'appels attendu si le Coach interroge Vigil à chaque inférence plutôt qu'en cache local ?
5. **Vectorisation de la BDD pour la recherche de contexte.** La question se posait pour la BDD Vigil (SQLite) ; elle se repose désormais pour la BDD Tradiaries (probablement déjà PostgreSQL côté Django ?) — recherche vectorielle (pgvector) dès v1, ou requêtes structurées classiques en attendant un besoin réel de passage à l'échelle ?
6. **Pistes de différenciation non challengées en profondeur** (transférées telles quelles, à reprendre avec un `/challenge` dédié avant toute décision) :
   - Plateforme intégrée permettant d'exécuter des trades directement là où sont le coach et les news scorées — scope majeur (accès à des comptes de trading, gestion de clés API d'exchange côté utilisateur, risque réglementaire potentiel selon juridiction).
   - Discussion live avec le coach adossée à une checklist de critères déterministes (« tant que X/Y critères ne sont pas validés, pas de prise de position ») : la partie checklist est cohérente avec le rule-checker v1 ; la partie « discussion live » réintroduit le risque de dérive déjà écarté du v1 côté Vigil — à re-challenger.

## Contrat côté Vigil (inchangé, à respecter depuis Tradiaries)

- Authentification par `VIGIL_BEARER_TOKEN` sur toutes les routes sauf `/api/health`.
- Rate limiting server-side (`VIGIL_RATE_LIMIT_PER_MINUTE`, défaut 30/min).
- Données servies exclusivement depuis la BDD Vigil (ingestion planifiée par cron, pas de fetch live sur requête) — fraîcheur variable selon la source (~2 min pour `crypto_prices`/`crypto_market`, ~10 min pour le reste).
- Aucun score directionnel haussier/baissier n'est produit par Vigil, en cohérence avec la contrainte « pas de conseil d'investissement » qui s'applique aussi au futur Coach.
- Détail complet : `docs/API_DOCUMENTATION.md` de ce repo.
