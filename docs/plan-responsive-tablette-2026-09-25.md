# Plan de refonte responsive — Tablette (769–1024px, et zone grise 600–768px)

**Date** : 2026-09-25
**Palier de rigueur** : Standard (voir `.ai/project-rules.md`)
**Statut** : Plan établi par analyse de code **et vérifié visuellement** (Claude in Chrome, viewport simulé 768×1024 / 900×1024 / 1024×768, compte de test `responsive_qa` avec données factices). Les bugs listés en section 1 ne sont plus des hypothèses — mesures DOM et captures d'écran à l'appui (résumées en 1.6). Reste à faire avant `/implementation` : vérifier au moins une fois sur un vrai appareil tablette (les mesures ont été prises via une iframe de taille fixe, pas un redimensionnement de fenêtre réel — voir note méthodologique en fin de document).
**Voir aussi** : `docs/plan-responsive-smartphone-2026-09-25.md` (partie smartphone du même chantier)

---

## 1. Diagnostic (issu de la lecture du code)

### 1.1 Trois systèmes de breakpoints incompatibles cohabitent

| Fichier | Breakpoints définis |
|---|---|
| `static/css/style.css` | tablette `769–1024px`, mobile `≤768px` |
| `static/css/investment.css` | tablette `600–1024px`, mobile `≤599px` |
| `static/css/trading.css` | bascule à `≤1024px` uniquement (pas de distinction tablette/mobile) |

**Conséquence concrète** : entre **600px et 768px** (tablettes portrait étroites, ex. petites tablettes Android ~600-720px), `investment.css` applique déjà son mode "tablette" (padding réduit, table compactée) alors que `style.css` traite encore ce viewport comme "desktop" — le sidebar reste à sa largeur desktop pleine tant qu'on n'atteint pas 769px. Résultat : une bande de largeurs où le rétrécissement de la sidebar et l'adaptation du contenu ne sont pas synchronisés. C'est une cause directe de l'affichage "mal aligné" signalé.

**Recommandation** : unifier sur **un seul jeu de seuils partagé** : `≤599px` = mobile, `600–1024px` = tablette, `>1024px` = desktop. Ce choix reprend les seuils déjà utilisés par `investment.css` (le fichier le plus complet aujourd'hui) et évite de retoucher la logique de conversion table→carte mobile déjà en place. Impact : ajuster `style.css` (768→599 et 769→600) et `trading.css` (ajouter la distinction si nécessaire), et aligner le seuil JS `isMobile` du composant menu (voir 1.2).

### 1.2 Sidebar : ouverte par défaut sur toute la plage tablette, jamais collapsée automatiquement

`components/side-menu.html` (script inline) ne considère "mobile" que `window.innerWidth <= 768`. Sur toute la plage tablette (769–1024px, et même 600–768px vu le seuil actuel), le menu s'ouvre donc **par défaut en pleine largeur** (240px via la media query tablette de `style.css`) et **reste ouvert** tant que l'utilisateur ne clique pas explicitement sur l'en-tête du menu pour le refermer. Sur une tablette 768–1024px de large, avec padding `.main-content` de 24px de chaque côté, il ne reste que **~500–560px** de largeur utile pour le contenu — largeur insuffisante pour les tableaux à colonnes multiples (voir 1.3).

C'est la cause racine de la remarque *« la bande du menu fermé prend beaucoup d'espace »* combinée à *« il faut scroll horizontalement »* : sur tablette, le menu n'est presque jamais réellement "fermé" par défaut, donc le contenu hérite systématiquement d'un espace utile réduit.

### 1.3 Tableaux multi-colonnes sans adaptation tablette réelle

Les pages `positions.html` (10 colonnes : Symbole/Date/Quantité/Prix entrée/Prix sortie/Direction/PnL/Exchange/Mode/Actions), `investment.html` (6 colonnes) et le tableau des positions ouvertes de `live_trading.html` (11 colonnes) utilisent `.investments-table`. La media query tablette de `investment.css` (`900–912`) ne fait que réduire `font-size` et `padding` — **aucune colonne n'est masquée ou réorganisée**. Avec ~500–560px de largeur utile (voir 1.2), un tableau à 10-11 colonnes en 13px ne peut pas tenir → scroll horizontal garanti, exactement le symptôme signalé.

Bonne nouvelle : la page Positions (`apps/positions/`) a déjà un panneau de détail cliquable en lecture seule (`static/js/positions-detail-panel.js`, `.detail-panel`/`.detail-panel-body`) qui affiche déjà toutes les données d'une ligne. C'est le point d'appui naturel pour retirer des colonnes secondaires du tableau sur tablette sans perdre d'information.

**Vérifié à 900px de large (compte de test avec données réelles)** : `.main-content` mesure `clientWidth: 650px` mais le tableau `.investments-table` force `scrollWidth: 811px` sur son conteneur — `.main-content` a un `overflow-x` calculé à `auto` (implicite : quand `overflow-y` est réglé et `overflow-x` ne l'est pas explicitement, le CSS impose `auto` sur les deux axes), donc **une barre de défilement horizontale apparaît bien**, contenue dans la zone de contenu plutôt que sur toute la page, mais le symptôme reste identique pour l'utilisateur : la colonne "Exchange" est tronquée hors champ, confirmé par capture d'écran (le en-tête de tableau s'arrête sur "EXCHAN...").

### 1.4 Page Trading : toolbar OK en largeur tablette, mais scroll vertical excessif en paysage

Vérifié à 900px de large : `.trading-chart-toolbar` (`select` + libellé symbole + 4 boutons d'intervalle) **tient sans problème**, pas de `flex-wrap` nécessaire à cette largeur — hypothèse initiale invalidée, aucune action requise ici pour la tablette (le `flex-wrap` reste nécessaire côté smartphone, voir l'autre document).

En revanche, vérifié à **1024×768** (iPad paysage) : le layout Trading bascule déjà en **colonne unique** à ce point exact (`static/css/trading.css:235`, `@media (max-width: 1024px)` — chart/toolbar et ticket empilés au lieu de côte à côte), et les hauteurs de graphique restent fixes en JS (`live_trading.html:322,329` : `480px` + `120px`). Mesure DOM : `.main-content` ne montre que **758px** de hauteur visible pour **1938px** de contenu total, et le bouton "Ouvrir la position" se trouve à **1567px** du haut — soit plus de deux hauteurs d'écran de scroll avant d'atteindre l'action principale du formulaire. Un iPad classique en paysage (1024×768) est une résolution tablette courante, pas un cas limite.

**Cause combinée** : (a) le seuil de bascule en colonne unique (`1024px`) est probablement trop généreux pour une tablette en paysage qui a largement la place de garder 2 colonnes (chart | ticket) jusqu'à une largeur plus étroite ; (b) même en colonne unique, les hauteurs de graphique fixes aggravent le problème. Recommandation révisée : réduire le seuil de bascule 1 colonne du workspace Trading (ex. `768px` au lieu de `1024px`, aligné sur le nouveau seuil mobile unifié de M1) **et** rendre les hauteurs de graphique adaptatives en colonne unique.

### 1.5 Composants secondaires à vérifier

- `.credential-item` (page Paramètres, `static/css/investment.css:865`) : flex row sans wrap — à vérifier avec une clé API longue + libellé sur tablette étroite.
- Tableaux imbriqués dans `.analytics-panel` (best/worst trade, PnL par direction/symbole/stratégie) héritent de la conversion mobile de `.investments-table` mais **sans `data-label`** → sur tablette ce n'est pas impacté (la conversion carte ne se déclenche qu'en `≤599px`), mais à garder en tête pour la partie smartphone.

---

## 2. Architecture concrète retenue

- **Un seul jeu de breakpoints** (`≤599` mobile / `600–1024` tablette / `>1024` desktop), appliqué de façon cohérente dans `style.css`, `investment.css`, `trading.css`, et repris dans la logique JS du menu (`components/side-menu.html`).
- **États du menu latéral à 3 niveaux** au lieu de 2 (ouvert/fermé) :
  1. **Desktop (>1024px)** : ouvert par défaut, comportement actuel inchangé.
  2. **Tablette (600–1024px, nouveau)** : **rail collapsé par défaut** (64px, icônes seules) — pas de texte, pas d'ouverture automatique. L'utilisateur ouvre en overlay ponctuel via le bouton toggle (le rail ne pousse plus le contenu, il flotte par-dessus comme sur mobile — voir 2.1).
  3. **Mobile (≤599px)** : drawer off-canvas complet (inchangé dans le principe, mais corrigé — voir doc smartphone pour le détail du bug de marge réservée).
- **Tableaux larges → priorisation de colonnes + panneau de détail**, plutôt que scroll horizontal ou re-empilement complet (le re-empilement en carte reste réservé au mobile, voir doc smartphone). Sur tablette, on garde un vrai tableau mais avec moins de colonnes visibles.
- **Nouveau composant réutilisable** : généraliser `positions-detail-panel.js` (aujourd'hui spécifique à `apps/positions`) en un composant partagé `static/js/row-detail-panel.js` + partiel `components/row-detail-panel.html`, paramétrable par une liste de champs `{label, value}` passée en `data-*` ou JSON par ligne. Réutilisé par : Positions (existant, à migrer), Investissements (nouveau), tableau des positions ouvertes de Trading (nouveau).

### 2.1 Sidebar tablette — comportement détaillé

- Rail collapsé (64px) par défaut sur 600–1024px, **par-dessus** le contenu (`position: fixed` ou équivalent), pas en layout grid poussant `.main-content` — pour ne jamais réserver de largeur morte comme actuellement.
- `.main-content` occupe donc la largeur pleine (moins le padding), le rail flotte avec un léger `box-shadow`/`backdrop-filter` pour rester lisible par-dessus le contenu au repos.
- Au clic sur le rail (ou sur une icône), le menu s'ouvre en overlay complet (comme mobile) avec un fond semi-transparent (`body::before` existant, à étendre à la plage tablette) — pas de push de contenu, pour éviter tout re-layout brusque des tableaux.
- Nécessite d'étendre le CSS existant `.side-menu:not(.hidden) ~ .main-content::before` (actuellement scopé `@media (max-width: 768px)` dans `style.css`) à la plage tablette, et de revoir le script `components/side-menu.html` pour distinguer 3 états au lieu de 2 (`isMobile` / nouveau `isTablet` / desktop).

---

## 3. Missions découpées et priorisées

### M1 — Unifier les breakpoints CSS *(bloquant, prérequis à tout le reste)*
- Fichiers : `static/css/style.css`, `static/css/investment.css`, `static/css/trading.css`.
- Remplacer les seuils `768/769` par `599/600` dans `style.css` pour aligner sur `investment.css`.
- Ajouter une distinction tablette/mobile explicite dans `trading.css` (actuellement un seul point de bascule à `1024px`) si les tests visuels (section 5) montrent un besoin réel de traitement différencié pour `.trading-workspace` entre mobile et tablette.
- Documenter les 3 seuils dans `.ai/project-rules.md` (section CSS) une fois validés, pour éviter la réapparition de systèmes divergents.

### M2 — Sidebar tablette en rail collapsé par défaut *(bloquant, gain UX le plus élevé)*
- Fichiers : `static/css/side-menu.css`, `static/css/style.css` (media query tablette), `components/side-menu.html` (script).
- Ajouter l'état "rail flottant" décrit en 2.1.
- Étendre l'overlay de fond (`body::before`) à la plage tablette.
- Vérifier la persistance localStorage existante (`tradiaries-menu-state`) reste cohérente avec le nouvel état à 3 niveaux (ne pas casser le comportement desktop/mobile déjà validé).

### M3 — Tableaux larges : priorisation de colonnes + panneau de détail *(bloquant, résout le scroll horizontal)*
- Nouveau composant partagé : `static/js/row-detail-panel.js` + `components/row-detail-panel.html` (généralisation de `positions-detail-panel.js`).
- Page Positions (`apps/positions/templates/positions/positions.html`) : sur tablette, masquer `Exchange` et `Mode` (déjà visibles au clic dans le panneau détail existant) ; garder Symbole/Date/Quantité/Entrée/Sortie/Direction/PnL/Actions.
- Page Investissements (`apps/investment/templates/investment/investment.html`) : ajouter un panneau de détail (n'existe pas aujourd'hui) et masquer une colonne secondaire sur tablette si nécessaire après vérification visuelle (le tableau a déjà peu de colonnes — 6 — donc impact probablement mineur, à confirmer).
- Tableau des positions ouvertes de `live_trading.html` (11 colonnes, le plus chargé) : masquer TP/SL sur tablette (déjà visibles via le formulaire de saisie juste au-dessus, redondance partielle) et exposer le détail complet via le nouveau panneau au clic sur une ligne.

### M4 — Page Trading : seuil de colonne unique + hauteurs de graphique adaptatives *(revu après vérification visuelle — pas de fix toolbar nécessaire sur tablette)*
- Fichiers : `static/css/trading.css`, `apps/live_trading/templates/live_trading/live_trading.html` (JS de création des charts).
- La toolbar (`.trading-chart-toolbar`) n'a **pas** besoin de `flex-wrap` sur la plage tablette (vérifié OK à 900px) — retiré du périmètre de cette mission.
- Abaisser le seuil de bascule en colonne unique de `.trading-workspace` (`static/css/trading.css:235`, actuellement `max-width: 1024px`) vers une valeur alignée sur M1 (ex. `768px`), pour qu'une tablette en paysage (1024×768, mesuré : 1938px de contenu pour 758px visibles, bouton de soumission à 1567px du haut) garde le layout 2 colonnes (chart | ticket) au lieu de tout empiler verticalement.
- En complément, hauteur de graphique réduite quand la colonne unique reste nécessaire (`--trading-chart-height` piloté par une media query plutôt qu'une valeur JS fixe à 480px), avec `chart.applyOptions({height: ...})` au resize.

### M5 — Ajustements de composants secondaires
- `.credential-item` (Paramètres) : `flex-wrap: wrap` + `gap` sur tablette pour éviter le débordement avec une clé API longue.
- Vérifier après M1 que les tableaux imbriqués `.analytics-panel table.investments-table` restent lisibles (pas de conversion carte avant 599px, donc impact tablette nul — à confirmer visuellement).

---

## 4. Niveaux de test requis (palier Standard)

Ce chantier est purement CSS/HTML/JS front — pas de test Python pertinent (`apps/*/tests.py` ne couvre pas le rendu visuel). Vérification manuelle requise :

1. Ouvrir Chrome, connecter l'extension Claude in Chrome (bloquant, voir statut en tête de doc).
2. Redimensionner à des résolutions tablette représentatives : `768×1024` (iPad portrait), `1024×768` (iPad paysage), `800×1280` (tablette Android portrait), `600×960` (zone grise basse de la plage tablette).
3. Pour chaque page (Dashboard, Positions, Investissements, Trading, Analytics, Journal, Paramètres) : capturer un screenshot, vérifier `document.documentElement.scrollWidth <= window.innerWidth` (pas de scroll horizontal involontaire), vérifier que le rail de menu ne recouvre pas de contenu interactif.
4. Vérifier le comportement d'ouverture/fermeture du rail (clic, overlay, fermeture par clic extérieur) sur au moins une page.
5. Après implémentation, mettre à jour `.ai/change-log.md` avec les résolutions testées et les éventuels écarts trouvés.

---

## 5. Points à signaler avant implémentation

- ✅ Vérification visuelle effectuée (voir 1.6) — les 3 bugs principaux (zone grise 768px, sidebar ouverte réduisant la largeur utile, tableaux qui débordent) sont confirmés par mesure DOM réelle, pas seulement supposés depuis le code.
- ⚠️ **Limite méthodologique à connaître** : le redimensionnement réel de la fenêtre Chrome (`resize_window`) ne fonctionnait pas dans cette session (fenêtre restée bloquée à 1920px quelle que soit la demande — probablement liée à l'environnement d'exécution). Les mesures ci-dessus ont été prises via une **iframe de taille fixe** injectée dans une page same-origin (contournement technique, cookies de session partagés donc authentification correcte), ce qui reproduit fidèlement les media queries CSS et `window.innerWidth` mais **pas** un vrai redimensionnement d'OS (pas de barre d'adresse mobile réelle, pas de clavier virtuel, etc.). Une vérification sur appareil physique ou émulateur Chrome DevTools classique reste recommandée avant mise en prod, en particulier pour M2 (comportement tactile du rail de menu).
- Le nouveau seuil unifié `600px` (M1) fait basculer en mode "tablette" des largeurs qui étaient traitées en "mobile" par `style.css` jusqu'ici (600–768px) — impact à vérifier spécifiquement sur le Dashboard (KPI grid, sidebar) qui utilise aujourd'hui le seuil `768/769` de `style.css`.
- Le choix de masquer des colonnes plutôt que de garder un scroll horizontal contenu (alternative plus rapide à implémenter : `overflow-x: auto` sur un wrapper de tableau avec première colonne `position: sticky`) n'a pas été challengé formellement — c'est une préférence UX (éviter tout scroll horizontal, cohérent avec la plainte initiale de l'utilisateur) plutôt qu'une contrainte technique. Si le panneau de détail généralisé (M3) s'avère trop lourd à développer pour la page Investissements, le repli scroll-horizontal-contenu + sticky column reste une option de secours à plus faible effort.

## 6. Résumé des preuves collectées (1.6)

| Test | Résolution | Résultat mesuré |
|---|---|---|
| Dashboard | 768×1024 | Menu masqué par défaut (mode mobile), KPI en 1 colonne — devrait être en mode tablette |
| Dashboard | 900×1024 | Menu ouvert 240px, KPI en 2 colonnes — comportement tablette correct |
| Positions | 900×1024 | `.main-content` clientWidth 650px / scrollWidth 851px, table scrollWidth 811px → colonne "Exchange" tronquée, scroll horizontal confirmé par capture |
| Trading | 900×1024 | Toolbar OK, pas de débordement |
| Trading | 1024×768 | Colonne unique activée, contenu total 1938px pour 758px visibles, bouton de soumission à 1567px du haut |
