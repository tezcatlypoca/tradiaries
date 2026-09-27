# Challenge — Refonte CSS/UX Tradiaries (2026-09-26)

**Source** : `docs/tradiaries_conversation_transcript.md` (retour utilisatrice Lucie, profil investisseuse retail non-experte, DCA/investissement long terme) + audit du CSS en place (`static/css/style.css`, `side-menu.css`, `trading.css`) + `apps/positions/templates/positions/positions.html`.

**Objectif de ce document** : challenger les pistes issues de la discussion avant tout gel de décision (`/decision-gel`). Rien ici n'est tranché — c'est la matière à trancher.

---

## 1. Constat sur le CSS actuel (base du challenge)

- **Thème sombre imposé, sans alternative** : `--page-bg: #080c10`, pas de variante claire, pas de `prefers-color-scheme`, pas de toggle. Confirme le retour de Lucie ("fond de page trop foncé").
- **Couleur primaire `--primary-color: #67e8c1`** (vert-menthe saturé) réutilisée absolument partout : titres de menu, bordures actives, focus, boutons, scrollbar, PWA icon, ET les graphiques de plusieurs pages différentes (dashboard, futures) — confirme le retour "même couleur que le reste des boutons" et "trop flashy/néon".
- **Une seule teinte positive/négative globale** (`--positive: #62e6ad`, `--negative: #ff8091`) : pas de palette étendue pour distinguer plusieurs séries sur un même graphique (investissement / spot / futures / all) → actuellement infaisable sans intervention CSS+JS de fond.
- **Table `positions.html`** : colonnes `Prix d'entrée` / `Prix de sortie` / `Direction` (texte "Long"/"Short") toujours présentes en vue liste — aucune colonne PNL calculée, aucun pictogramme directionnel. Exactement la surcharge visuelle que Samuel proposait de retirer pendant l'échange.
- **Pas de composant "camembert / répartition par actif"** dans le code actuel (recherche négative) — c'est une idée neuve, pas un existant à retoucher.
- **Menu bilingue de fait** (dashboard/analytics/trading en anglais, position/journal en français) sans mécanisme de langue dans Paramètres.
- **Logos de menu** : à vérifier visuellement (non challengé ici, jugement esthétique pur — pas de risque technique identifié à démonter).

---

## 2. Incohérences et risques identifiés dans les pistes de la discussion

### 2.1 "Fond clair + pastel" pour une app de trading — risque de lisibilité financière
- **Risque** : les codes couleur pastel (vert/rouge doux) réduisent le contraste perçu entre gain/perte — critique sur une plateforme où l'utilisateur doit lire un PNL en un coup d'œil, potentiellement en conditions de luminosité variables (mobile en extérieur). La quasi-totalité des plateformes de trading pro (Kraken, Binance, TradingView, Trade Republic) restent en dark mode par défaut précisément pour ce contraste, et parce que l'usage est souvent prolongé/nocturne.
- **Alternative à challenger** : garder un **dark mode par défaut** (déjà en place, cohérent avec la référence Trade Republic elle-même citée par Lucie — qui est en dark) et proposer un **light mode optionnel** plutôt qu'un remplacement pur et simple. Ça répond au retour "trop foncé" sans sacrifier le contraste pour l'usage intensif, et ça évite de refaire tout le travail de contraste WCAG deux fois dans le mauvais sens.
- **Coût technique** : un vrai dark/light toggle propre nécessite de transformer TOUTES les couleurs codées en dur du CSS (`#0e141b`, `#131a22`, etc., visibles dans `trading.css` en fallback de `var()`) en variables sur `:root`/`[data-theme]`, cf. `--positive/--negative` qui doivent aussi rester lisibles sur les deux fonds. C'est un chantier CSS transverse, pas une passe de couleurs.
- **Faisabilité** : moyenne — le projet a déjà une architecture de variables CSS centralisée (`style.css` `:root`), donc la fondation existe, mais AUCUNE des couleurs de `trading.css`/templates n'est actuellement garantie de suivre ces variables (fallbacks codés en dur observés).

### 2.2 "Enlever le vert flashy partout" vs cohérence de marque
- **Risque** : `--primary-color` est utilisé à la fois comme **couleur de marque** (logo, titres) et comme **couleur sémantique** (bouton actif, focus, PWA). Changer la teinte pour du pastel affecte aussi la lisibilité des états actifs du menu (`rgba(103, 232, 193, 0.1)` pour l'item actif) — un pastel trop doux risque de rendre l'état actif du menu indiscernable, régressant sur un problème déjà résolu ("où suis-je dans le menu").
- **Alternative à challenger** : séparer explicitement **couleur de marque** (peut rester distinctive, moins saturée) de **couleur d'état actif/focus** (doit rester à fort contraste, teste WCAG AA minimum) — deux tokens au lieu d'un seul `--primary-color` réutilisé partout.

### 2.3 Multi-courbes avec sélection/désélection sur le dashboard — complexité sous-estimée
- **Risque non résolu dans la discussion** : Samuel lui-même pointe le vrai obstacle — les échelles de valeur (BTC à 60k vs un portefeuille à 700€) rendent la superposition de courbes illisible sans axe secondaire ou normalisation. La conversation valide l'idée de "cocher/décocher + couleurs différentes" (fonctionnalité UI simple, type légende cliquable Chart.js/ECharts) MAIS ne résout PAS le vrai problème d'échelle qui a motivé la séparation actuelle des vues.
- **Alternative à challenger** : normaliser en **% de variation depuis la date de départ commune** plutôt qu'en valeur absolue quand plusieurs séries hétérogènes sont affichées ensemble — c'est la solution standard (Trade Republic, tout tracker de portefeuille) pour comparer des séries d'échelles différentes sans axe double. À trancher avant tout travail CSS sur ce composant : sinon on livre un toggle qui ne règle pas le problème réel.
- **Faisabilité** : dépend du gestionnaire de graphique déjà en place (à vérifier — non audité ici) ; ajouter un mode "normalisé" est un changement de logique de données, pas juste de style.

### 2.4 Fusion de l'affichage Spot/Futures dans "Position" — risque de sur-densification
- **Risque** : l'idée validée dans l'échange ("une carte divisée en deux, spot en haut/futures en bas" ou "deux colonnes côte à côte") résout le problème d'aller-retour, mais double la densité d'info sur une page déjà identifiée comme surchargée ("beaucoup de texte, beaucoup d'informations"). Sans réduction préalable des colonnes (§2.5), fusionner Spot+Futures sur la même vue aggrave le problème qu'on essaie de résoudre par ailleurs.
- **Alternative à challenger** : séquencer les deux chantiers plutôt que les traiter comme une seule tâche CSS — d'abord alléger la table (retirer prix entrée/sortie de la liste, ajouter PNL + pictogramme directionnel, cf. §2.5), *ensuite* juger si la fusion Spot/Futures reste nécessaire ou si l'allègement suffit à rendre l'aller-retour supportable.

### 2.5 Retirer prix d'entrée/sortie, ajouter PNL + picto directionnel — validé mais sous-spécifié
- **Point positif** : cette piste est la plus concrète et actionnable de toute la discussion, et cohérente avec l'objectif de "tableau plus fin". Faisabilité haute : donnée déjà présente en base (`entry_price`, `exit_price` déjà stockés), il s'agit d'un calcul d'affichage (`exit_price - entry_price`) et d'un remplacement de colonnes dans `positions.html`.
- **Point non tranché à challenger** : le PNL affiché doit-il être en **valeur absolue** (€/$) ou en **%** ? La discussion mélange les deux ("moins vingt-cinq" pourrait être lu comme -25€ ou -25%) — ambiguïté à trancher avant implémentation, sinon retour utilisateur garanti après livraison.
- **Risque UX du picto pur (taureau/ours)** : Lucie elle-même propose d'associer le symbole à un **texte-clé déjà connu du grand public trading** (bull/bear), mais le persona cible de Lucie est justement une non-experte qui ne connaît pas ce jargon avant la conversation ("Ok, ça, c'est clair, ouais" — elle apprend le terme en direct). Remplacer purement "Long/Short" par une icône bull/bear sans légende texte risque de rendre l'info **moins** accessible pour le persona explicitement visé (retail débutant), pas plus.
- **Alternative à challenger** : icône + micro-label (flèche ↑/↓ ou tête stylisée + "Long"/"Short" en petit), pas une pure substitution icône-sans-texte. Réconcilie "moins de texte" et "accessible aux non-experts".

### 2.6 Camembert de répartition par actif avec drill-down au clic
- **Risque de sur-ingénierie à ce stade** : c'est une fonctionnalité de data-viz + navigation (filtrage par symbole) en plus d'un changement CSS — largement hors scope d'une "refonte CSS". La discussion elle-même le reconnaît en fin d'échange ("ça s'affine, ça se fait pas en one shot").
- **Alternative à challenger** : traiter le camembert comme un chantier **fonctionnel séparé** (à instruire via `/degrossir` dédié, avec la donnée de filtrage par symbole qui manque déjà aujourd'hui — "je peux pas filtrer" est mentionné explicitement dans la conversation comme un manque actuel), pas comme un item de la refonte visuelle. Mélanger les deux dans un seul chantier CSS risque de bloquer la livraison de la partie purement visuelle (palette, thème, table) derrière une fonctionnalité de filtrage qui n'existe pas encore.

### 2.7 Renommage "Position" → autre terme
- **Risque** : aucune alternative proposée dans l'échange n'a convaincu ni Samuel ni Lucie ("balance" évoqué puis abandonné). Renommer sans meilleure option validée = churn de navigation (URL, menu, tests) pour un problème de terme non résolu.
- **Alternative à challenger** : garder "Position" mais ajouter un sous-titre/description courte sous le libellé de menu (pattern déjà existant ailleurs dans l'app avec `.dashboard-container > p`) plutôt que de rouvrir un renommage sans consensus.

### 2.8 Bilinguisme FR/EN incohérent
- **Constat** : c'est un vrai problème identifié par les deux participants, mais la solution proposée ("tout en français + sélecteur de langue dans Paramètres") est un chantier d'**internationalisation (i18n)**, pas un chantier CSS. Django a un support i18n natif (`{% trans %}`, `django.utils.translation`) — le rattacher artificiellement à la refonte visuelle risque de faire déraper le scope.
- **Alternative à challenger** : traiter dans l'immédiat uniquement l'harmonisation des libellés de menu existants (renommer les 2-3 termes anglais restants en français, ou l'inverse — cohérence lexicale, pas mécanisme de traduction), et reporter le sélecteur de langue multi-locale à un chantier i18n dédié.

---

## 3. Analyse concurrentielle (le projet a un objectif commercial potentiel — cf. `decisions.md`, "Commercialisation potentielle de Tradiaries", en suspens)

- **Trade Republic** (référence explicite de Lucie) : dark UI, palette restreinte, filtres temporels 1j/1sem/1mois/1an/all déjà identiques à ceux de Tradiaries et validés comme pertinents par Lucie elle-même — pas de changement à challenger ici, le pattern est déjà bon.
- **TraderSync / Cypher, TradesViz** (déjà identifiés dans `docs/coach-ia-vers-tradiaries-2026-09-25.md` comme concurrents directs sur le versant analytics/coaching) : plateformes orientées trader actif/semi-pro, UI dense de type "tableau de bord pro" — PAS le persona pastel/ludique demandé par Lucie. Ça confirme une tension déjà présente dans l'échange lui-même : Samuel pose la question sans la trancher ("à qui se dédie réellement le truc ?").
- **Risque stratégique central, à trancher avant tout travail de palette** : le positionnement produit n'est pas figé. Un design "pastel, ludique, accessible à tous" (persona Lucie — DCA, 5-200€/mois) et un design "dense, dark, orienté trader actif" (persona attendu des concurrents identifiés et du propre usage futures/analytics de Samuel) sont **deux directions incompatibles au niveau du système de couleurs et de la densité d'info**. Faire un compromis flou entre les deux risque de satisfaire ni l'un ni l'autre segment.
- **Alternative à challenger** : trancher le persona primaire de la V1 commercialisable avant de figer une palette. Deux options concrètes :
  - **A) Un seul thème, orienté "trader actif" (dark, dense, proche des standards Kraken/TradingView)** — cohérent avec le fait que Samuel construit déjà des features avancées (futures LIVE, analytics par stratégie/actif, coaching IA à venir) qui sont typiquement des besoins de trader actif, pas de DCA occasionnel.
  - **B) Deux modes de densité selon le profil déclaré à l'inscription (investisseur DCA vs trader actif)** — plus fidèle aux deux retours recueillis (Lucie = DCA, Samuel = actif) mais double le travail de design ET de maintenance CSS, et retarde la V1.
- **Point non financier mais bloquant identifié en creux dans la conversation** : Samuel évoque lui-même un risque réglementaire (passage d'ordres = statut d'exchange régulé ?) qui conditionne si la plateforme reste un outil d'agrégation/journal (comme aujourd'hui) ou devient un vrai point d'exécution d'ordres. Ce n'est pas un sujet CSS, mais **le positionnement produit (§ ci-dessus) ne peut pas être tranché indépendamment de cette question** — l'UI d'un simple journal/dashboard et celle d'une plateforme d'exécution d'ordres n'ont pas la même densité ni les mêmes composants (ticket d'ordre déjà présent dans `trading.css` suppose déjà l'exécution).

---

## 4. Implications techniques, maintenabilité, coûts

- **Palette actuelle déjà centralisée** en variables CSS (`:root` dans `style.css`) — bon point de départ, mais `trading.css` a des couleurs codées en dur en fallback de `var()` (ex. `background: var(--surface-2, #131a22)`) : un simple changement de variable ne suffira pas à tout retexturer, il faut auditer/supprimer ces fallbacks avant tout changement de thème.
- **Coût de test** : la refonte responsive tablette/mobile vient d'être livrée (2026-09-25, cf. `plan-responsive-*`) avec des seuils de breakpoint mesurés précisément (ex. 767px pour `trading.css`, 599px pour le menu). Un changement de palette ne remet pas en cause ces seuils, mais un changement de **densité** de table (§2.5, §2.4) le pourrait — à revalider sur mobile après tout changement de colonnes.
- **Pas de dette de test unitaire concernée** : ce chantier est visuel/template, hors périmètre de la suite `apps/core/tests.py` déjà étoffée récemment (2026-09-22) — bon point, aucun risque de régression testée à anticiper au-delà d'une vérification manuelle visuelle multi-device.

---

## 5. Synthèse — ce qui reste à trancher via `/decision-gel`

1. Thème : dark par défaut + light optionnel, vs remplacement pur par un thème clair pastel (§2.1).
2. Séparation couleur de marque / couleur d'état actif (§2.2).
3. Dashboard multi-courbes : mode normalisé (%) requis avant tout toggle cocher/décocher (§2.3).
4. Séquencement : alléger la table Position (PNL + picto, §2.5) AVANT de juger la fusion Spot/Futures (§2.4).
5. PNL affiché en valeur ou en % (§2.5) — à trancher explicitement.
6. Picto directionnel : icône seule vs icône + micro-label texte (§2.5).
7. Camembert de répartition : sortir du scope "refonte CSS", traiter comme chantier fonctionnel séparé (§2.6).
8. Renommage "Position" : abandonner l'idée faute d'alternative validée, ou ajouter un sous-titre explicatif (§2.7).
9. Bilinguisme : harmonisation lexicale immédiate vs chantier i18n complet différé (§2.8).
10. **Persistant/bloquant** : trancher le persona primaire (DCA occasionnel vs trader actif) avant de figer une direction de palette/densité — sans quoi toute décision de style ci-dessus reste provisoire (§3).
