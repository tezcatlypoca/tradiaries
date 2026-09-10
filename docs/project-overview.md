# Tradiaries

## Résumé

Tradiaries est une application Django de suivi des investissements et du trading pour les traders particuliers. Elle centralise les prises de position, les informations qui motivent ces prises de position, leur résultat et les statistiques de performance.

L'objectif principal n'est pas de promettre de meilleurs rendements. L'application aide plutôt l'utilisateur à :

- garder une trace fiable de ses opérations ;
- distinguer l'investissement, le trading spot et le trading futures ;
- comparer ses résultats réels et simulés ;
- mesurer l'application de ses stratégies ;
- identifier ses habitudes et ses erreurs répétées ;
- construire une pratique de trading plus structurée et plus disciplinée.

Le produit peut donc être positionné comme un **journal de trading augmenté**, puis comme un **coach de discipline et de processus**.

## Fonctionnalités actuelles

### Dashboard portefeuille

Le dashboard fournit une vue synthétique du portefeuille réel :

- valeur actuelle du portefeuille ;
- capital investi ;
- PnL global ;
- graphique d'évolution du capital cumulé investi ;
- signalement des symboles dont le prix n'est pas disponible.

Le résumé global inclut les investissements simples, les positions spot LIVE et les positions futures LIVE. Les positions PAPER sont conservées dans le journal mais exclues de cette vision du portefeuille réel.

> Le graphique historique représente le capital cumulé investi. Il ne s'agit pas d'une valorisation historique mark-to-market, car l'application ne conserve pas encore d'historique de prix passé.

### Investissements simples

Le module Investment permet d'enregistrer des achats et des ventes ponctuels :

- symbole ;
- quantité ;
- prix ;
- action achat ou vente ;
- date ;
- notes ;
- référence externe éventuelle.

Les statistiques calculent les quantités nettes par symbole, le capital investi, la valeur actuelle et le PnL à partir des prix courants disponibles sur Kraken.

### Trading spot

Le module Spot Trading permet de suivre des positions spot :

- symbole, quantité et prix d'entrée ;
- prix de sortie, avec possibilité d'une seconde sortie ;
- exchange ;
- notes ;
- take profit et stop loss ;
- mode PAPER ou LIVE ;
- séparation des positions ouvertes et clôturées ;
- PnL réalisé, latent et total ;
- filtres par mode de trading.

Le spot est traité comme une position LONG à l'ouverture. Les statistiques peuvent s'appuyer sur le prix courant récupéré via Kraken.

### Trading futures

Le module Futures Trading ajoute les éléments propres aux contrats futures :

- direction LONG ou SHORT ;
- ratio risque/rendement ;
- ressenti du trader, de très haussier à très baissier ;
- raison de la prise de position ;
- stratégie utilisée, par exemple `IRC 4h` ou `VP 15min` ;
- mode PAPER ou LIVE ;
- take profit et stop loss ;
- calcul du PnL selon la direction.

Le mode PAPER permet de tester une méthode sans envoyer d'ordre réel. Le mode LIVE est distingué dans les données et les statistiques, afin d'éviter de mélanger expérimentation et argent réel.

### Trading live et gestion TP/SL

La page `/live/` permet :

- d'ouvrir une position spot PAPER ou LIVE ;
- d'ouvrir une position futures PAPER ;
- de suivre les positions ouvertes avec leurs prix courants et leur PnL latent ;
- de clôturer une position ;
- de définir un take profit et un stop loss ;
- de valider une checklist de stratégie avant un ordre spot LIVE.

Les ordres spot LIVE sont envoyés à Kraken classic. Les niveaux TP/SL sont surveillés par un processus séparé (`watch_tp_sl`) qui clôture la position lorsque le niveau est atteint. Les futures LIVE ne sont pas encore implémentés, car ils nécessitent l'API Kraken Futures et des clés distinctes.

Une checklist IRC 4h exige au moins deux critères sur trois pour confirmer un ordre LIVE : régime, SAR et volume profile. Cette étape sert de garde-fou comportemental, pas de garantie de résultat.

### Analytics futures

La page Analytics analyse les positions futures clôturées, en distinguant LIVE et PAPER :

- nombre de positions clôturées et ouvertes ;
- win rate ;
- profit factor ;
- R moyen ;
- gain moyen et perte moyenne ;
- PnL total réalisé ;
- meilleur et pire trade ;
- ventilation par stratégie, symbole, ressenti et direction.

Ces indicateurs servent à évaluer la qualité passée du processus, avec la prudence nécessaire sur les petits échantillons et les résultats historiques.

### Journal de trading

Le Journal affiche les trades futures par ordre chronologique et permet de filtrer par :

- mode LIVE ou PAPER ;
- stratégie ;
- symbole.

Chaque trade clôturé affiche son PnL calculé. Les champs `why`, `feeling` et `strategy` constituent déjà une base utile pour analyser la qualité des décisions, au-delà du seul résultat financier.

### Import et synchronisation

Le projet prévoit plusieurs moyens d'alimenter le journal :

- import de l'historique Kraken dans les investissements simples ;
- import CSV de données d'investissement ;
- import d'un journal futures exporté depuis Notion ;
- déduplication des opérations grâce aux références externes ou à une clé métier.

La synchronisation Kraken est disponible via la commande Django `import_kraken_trades`. Elle est conçue pour être idempotente et ne pas recréer les trades déjà importés.

### Gestion des clés API

Les clés API sont gérées depuis la page Paramètres :

- plateformes prévues : Kraken, Binance, Bitget, CoinMarketCap et autres ;
- clé, secret et passphrase selon la plateforme ;
- stockage chiffré en base ;
- affichage masqué de la clé ;
- gestion séparée des identifiants Kraken utilisés par le client API.

### Sécurité et exploitation déjà présents

Le projet dispose notamment de :

- authentification sur les pages métier ;
- protection des opérations par méthodes HTTP ;
- endpoint `/healthz/` ;
- gestion des erreurs réseau Kraken, timeouts, retries limités et cache des prix ;
- logs applicatifs sans journalisation volontaire des clés API ;
- commandes Django pour les tâches hors requête web.

## Architecture fonctionnelle

Le projet est organisé autour de Django et de plusieurs apps spécialisées :

```text
dashboard       Vue globale du portefeuille et paramètres
investment      Investissements simples
spot_trading    Positions spot
futures_trading Positions futures
live_trading    Ouverture et suivi des positions live/paper
analytics       Statistiques futures
journal         Journal filtrable des trades futures
core            Modèles, formulaires, API Kraken et services métier
```

Les modèles métier principaux sont centralisés dans `apps/core` : `SimpleInvestment`, `SpotTrading`, `FuturesTrading` et `ApiCredential`. Le service de portefeuille agrège les données et calcule les statistiques, tandis que le service de trading orchestre l'ouverture, la clôture et la surveillance des positions.

## Proposition : le coach IA de discipline

### Positionnement produit

Le coach IA serait un assistant personnel qui aide le trader retail à **mieux suivre le plan qu'il s'est lui-même fixé**.

Il ne devrait pas être présenté comme :

- un fournisseur de signaux ;
- un conseiller financier personnalisé ;
- un système capable de prédire le marché ;
- une garantie de gains ;
- un outil d'optimisation automatique des performances.

La promesse commerciale est plus crédible et plus simple à expliquer :

> Tradiaries vous aide à comprendre vos décisions, à repérer vos écarts de discipline et à appliquer plus régulièrement vos propres stratégies.

### Données que le coach peut exploiter

Le coach peut travailler à partir de données déjà présentes dans l'application :

- historique des positions et résultats ;
- mode PAPER ou LIVE ;
- stratégie déclarée ;
- direction LONG ou SHORT ;
- raison de la prise de position ;
- ressenti avant l'entrée ;
- prix d'entrée, TP, SL et ratio risque/rendement ;
- respect ou non de la checklist IRC ;
- durée et issue des positions ;
- écarts entre trades prévus et trades réellement exécutés ;
- statistiques par stratégie, symbole, direction et contexte.

Il pourrait également demander une courte note après la clôture : ce qui était prévu, ce qui a été fait, ce qui a été ressenti et ce qui devra être changé la prochaine fois.

### Cas d'usage concrets

#### Avant l'entrée

Le coach pose quelques questions structurées :

- Quelle stratégie est utilisée ?
- Quels critères sont présents ?
- Où se trouvent l'invalidation, le TP et le SL ?
- Quel est le risque accepté ?
- L'entrée respecte-t-elle les règles habituelles de cette stratégie ?
- Le ressenti actuel risque-t-il d'influencer la décision ?

Il peut signaler une incohérence, par exemple un trade déclaré comme `IRC 4h` sans critères renseignés, ou un ratio risque/rendement inhabituel par rapport aux trades précédents. Il doit laisser la décision finale à l'utilisateur.

#### Pendant la position

Le coach peut rappeler le plan initial :

- niveau d'invalidation ;
- TP et SL prévus ;
- raisons d'entrée ;
- règle de gestion indiquée par l'utilisateur.

Il peut demander une confirmation avant une modification impulsive, sans déplacer automatiquement le stop, clôturer ou ouvrir une position.

#### Après la clôture

Le coach transforme le trade en retour d'expérience :

- le plan a-t-il été respecté ? ;
- la sortie correspondait-elle au scénario initial ? ;
- l'utilisateur a-t-il déplacé son SL ou poursuivi une perte ? ;
- quelle règle a été appliquée ou enfreinte ? ;
- quel enseignement est réutilisable ?

#### Revue hebdomadaire

Une synthèse peut mettre en évidence des régularités :

- davantage d'écarts sur une stratégie donnée ;
- entrées tardives après une série de pertes ;
- résultats très différents entre PAPER et LIVE ;
- meilleure discipline lorsque le risque est défini avant l'entrée ;
- surreprésentation d'un symbole ou d'une direction ;
- écart entre le ressenti déclaré et les résultats observés.

Le ton doit rester descriptif, factuel et non culpabilisant. Le coach doit parler de comportements observables, pas poser de diagnostic psychologique.

## MVP recommandé pour le coach IA

Une première version peut rester simple et utile :

1. Ajouter une page ou un panneau `Coach` dans le Journal.
2. Générer un briefing avant entrée à partir du formulaire de trade et de la stratégie sélectionnée.
3. Générer une revue après clôture avec cinq questions maximum.
4. Produire une synthèse hebdomadaire fondée sur les trades clôturés.
5. Afficher les observations avec les trades concernés et les données sources.
6. Demander une confirmation explicite avant toute action sensible.

La première version ne devrait ni passer d'ordre, ni modifier un trade, ni calculer seule une taille de position présentée comme correcte. Elle doit d'abord être un outil de réflexion et de suivi.

## Garde-fous nécessaires

- Séparer clairement faits, calculs et suggestions générées par le modèle.
- Afficher la date et l'échantillon utilisé pour chaque observation.
- Signaler les échantillons trop faibles pour conclure.
- Ne jamais promettre un gain ou un taux de réussite futur.
- Ne pas transformer une corrélation historique en règle de trading.
- Ne pas envoyer de données ou de secrets API au fournisseur IA.
- Anonymiser les données envoyées au modèle et minimiser leur volume.
- Conserver l'historique des recommandations affichées et des réponses de l'utilisateur.
- Prévoir un mode désactivé et une suppression des données conversationnelles.
- Garder les validations métier et les blocages LIVE côté serveur, indépendamment de l'IA.

## Limites et chantiers avant une diffusion large

Le projet est fonctionnel pour un usage de développement et de journal personnel, mais plusieurs sujets doivent être traités avant une exposition publique ou une utilisation multi-utilisateur :

- rattacher les investissements et trades à un utilisateur ;
- renforcer les permissions objet ;
- définir précisément frais, devise de référence, marge et levier ;
- formaliser les sorties partielles et le calcul de `exit_price_2` ;
- ajouter des tests métier et de permissions plus complets ;
- sortir les synchronisations et le watcher dans une infrastructure de tâches fiable ;
- passer à PostgreSQL et mettre en place sauvegardes et restauration ;
- finaliser HTTPS, configuration des secrets, monitoring et CI ;
- documenter les limites réglementaires et le positionnement non-conseil de l'IA.

## Vision produit

Tradiaries peut évoluer en trois niveaux :

1. **Journal fiable** : enregistrer et centraliser les investissements et trades.
2. **Analyse du processus** : mesurer les résultats et les écarts aux stratégies.
3. **Coaching comportemental** : aider le trader à préparer, exécuter et revoir son plan avec davantage de constance.

Cette progression donne une proposition de valeur claire : Tradiaries ne prétend pas savoir mieux que le marché. Il aide l'utilisateur à mieux connaître sa propre manière de trader et à devenir plus constant dans l'application de ses règles.