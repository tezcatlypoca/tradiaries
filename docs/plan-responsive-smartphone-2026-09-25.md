# Plan de refonte responsive — Smartphone (≤599px, et vigilance 600–768px en paysage)

**Date** : 2026-09-25
**Palier de rigueur** : Standard (voir `.ai/project-rules.md`)
**Statut** : Plan établi par analyse de code **et vérifié visuellement** (Claude in Chrome, viewport simulé 390×844, compte de test `responsive_qa` avec données factices). Les bugs 1.1, 1.2 et 1.3 sont confirmés par mesure DOM et capture d'écran, plus seulement déduits du code — voir preuves en 1.5. Limite méthodologique : voir note en fin de document (redimensionnement réel de fenêtre indisponible dans cette session, simulation par iframe utilisée à la place).
**Prérequis** : ce document suppose que **M1 (unification des breakpoints)** de `docs/plan-responsive-tablette-2026-09-25.md` est traité en premier, car il redéfinit le seuil mobile/tablette utilisé ici (`≤599px`).

---

## 1. Diagnostic (issu de la lecture du code)

### 1.1 Bug de layout confirmé : le menu "fermé" réserve quand même 64px en permanence

C'est la cause directe et vérifiable dans le code de la plainte *« la bande du menu fermé prend beaucoup d'espace »*.

Dans `static/css/style.css`, le bloc mobile (`@media (max-width: 768px)`) définit :

```css
.main-content {
    margin-left: var(--sidebar-width); /* 264px si menu "ouvert" */
}
.side-menu.hidden ~ .main-content,
.main-content.expanded {
    margin-left: var(--sidebar-collapsed-width); /* 64px si menu "fermé" */
}
```

Le script `components/side-menu.html` ferme le menu par défaut sur mobile (`isMobile = innerWidth <= 768`, `shouldBeClosed = true` par défaut). Mais "fermé" ne veut pas dire "sans espace réservé" : le sélecteur CSS `.side-menu.hidden ~ .main-content` s'applique dès que `.side-menu` a la classe `hidden` — ce qui est le cas par défaut sur mobile — et impose **64px de marge gauche en permanence**, alors que le menu est censé être entièrement hors écran (`transform: translateX(...)`) et remplacé par un simple bouton hamburger flottant (`.menu-toggle`, `position: fixed`).

Concrètement, sur un iPhone standard (375-390px de large), **64px sur ~375-390px (≈ 17%) sont perdus en permanence** pour une bande vide qui ne sert à rien visuellement (le menu est transformé hors champ, `.menu-list`/`.menu-header` sont à `opacity: 0`). C'est une régression de layout, pas un choix voulu — le collapsed-rail à 64px a du sens sur desktop (icônes visibles, sidebar réellement rétrécie) mais n'a aucun sens sur mobile où le menu est un drawer complet, pas un rail.

**Vérifié à 390×844 (compte de test)** : mesure DOM confirmée — `.side-menu` a bien la classe `hidden` (menu fermé) mais `.main-content` a `margin-left: 64px` en style calculé, avec `clientWidth: 316px` sur 390px de large disponibles. Capture d'écran à l'appui : une bande sombre vide occupe le côté gauche de l'écran, avec uniquement le bouton hamburger flottant dedans — exactement le symptôme signalé.

### 1.2 Tableaux : conversion "carte" en place, mais sans libellés sur 3 pages sur 5

`investment.css` (`@media (max-width: 599px)`) convertit déjà `.investments-table` en liste de cartes verticales (`display:flex; flex-direction:column`), avec des libellés de colonne injectés via `td::before { content: attr(data-label) }`. Ce mécanisme **fonctionne** mais dépend d'un attribut `data-label="..."` posé manuellement sur chaque `<td>` du template.

| Page | `data-label` posé ? |
|---|---|
| `apps/spot_trading/templates/spot_trading/spot_trading.html` | ✅ |
| `apps/futures_trading/templates/futures_trading/futures_trading.html` | ✅ |
| `apps/investment/templates/investment/investment.html` | ❌ |
| `apps/positions/templates/positions/positions.html` | ❌ |
| `apps/live_trading/templates/live_trading/live_trading.html` (tableau positions ouvertes) | ❌ |

Sur ces 3 dernières pages, en `≤599px`, chaque ligne devient une carte affichant une pile de valeurs brutes **sans savoir laquelle est laquelle** (ex. `"BTCUSD"`, `"25/09/2026"`, `"0.05"`, `"$67000"` empilés sans étiquette). C'est directement le symptôme *« composants mal affichés »* sur mobile pour ces 3 pages — le mécanisme existe déjà dans le CSS, il manque juste le balisage HTML côté template. Correction peu coûteuse et à fort impact.

**Vérifié à 390×844 sur la page Positions (données de test réelles)** : capture d'écran à l'appui, une carte affiche littéralement `ETHUSD` / `24/09/2026` / `1.00000000` / `$3100.00000000` / `$3050.00000000` / `Kraken` empilés sans aucun libellé — impossible de savoir que `$3100` est le prix d'entrée et `$3050` le prix de sortie sans deviner depuis l'ordre.

### 1.3 Page Trading : plusieurs points de friction spécifiques au mobile

- **Toolbar du graphique sans wrap, confirmé** (`static/css/trading.css:27`, `.trading-chart-toolbar`) : `select` d'actif (min-width 120px) + libellé symbole (`flex:1`) + 4 boutons d'intervalle en ligne, sans `flex-wrap`. Vérifié à 390×844 : la toolbar a besoin de `374px` (`scrollWidth === clientWidth`, donc pas de wrap interne, juste un débordement) alors que son conteneur `.investments-container` n'offre que `284px` de large (déjà réduit par le bug de marge du menu, section 1.1) → `scrollWidth: 382px` sur le conteneur, une barre de défilement horizontale apparaît, confirmée par capture (les boutons "4h" et "1D" sont poussés hors champ, seuls "15m"/"1h" restent visibles). **Les deux bugs se cumulent** : même après correction du bug de marge (M1, ~348px disponibles), la toolbar à 374px déborderait encore légèrement — le `flex-wrap` (M4) reste nécessaire indépendamment de M1.
- **Graphiques à hauteur fixe** (`live_trading.html:322,329` : `height: 480` + `height: 120`, en JS, jamais recalculée par media query) : sur un écran de ~700-800px de haut avec barre d'adresse mobile, header et toolbar, le bloc graphique (600px) + la carte ticket qui suit peuvent nécessiter un scroll vertical très long avant d'atteindre le formulaire de prise de position ou les positions ouvertes.
- **Formulaire ticket long** : Spot/Futures toggle, direction, mode, 4 champs numériques, aperçu risque (grid 3 colonnes), 2 sections `<details>` repliables (déjà un bon point), bouton de soumission — tout cela s'empile verticalement sous le graphique. Pas de bug à proprement parler, mais un parcours long avant d'atteindre l'action principale ("Ouvrir la position").
- **`.trading-risk-preview`** (`grid-template-columns: repeat(3, 1fr)`, toujours actif) : 3 colonnes de type `Risque / Gain potentiel / Ratio R/R` avec des valeurs en `$` — à vérifier visuellement en dessous de ~340px de large (probablement tenable mais serré).

### 1.4 Zone grise : téléphones en orientation paysage (600–900px de large)

Un téléphone moderne en paysage peut facilement dépasser 599px de large (ex. ~740-930px selon les modèles). Avec le nouveau seuil unifié proposé (`≤599` mobile / `600–1024` tablette), ces sessions basculeront en **mode tablette** (rail collapsé, tableaux avec colonnes masquées — voir doc tablette) plutôt qu'en mode carte mobile. C'est cohérent avec la largeur réelle disponible (un rail 64px + contenu large est plus adapté qu'un empilement de cartes sur 700-900px), mais **à vérifier visuellement** — c'est un vrai angle mort du testing habituel (on teste rarement le paysage) et une régression y serait facilement invisible sans vérification dédiée. Non testé dans cette passe (priorité donnée aux bugs confirmés 1.1-1.3) — reste dans le périmètre de M5.

### 1.5 Résumé des preuves collectées

| Test | Résolution | Résultat mesuré |
|---|---|---|
| Dashboard | 390×844 | `.side-menu.hidden` mais `margin-left: 64px` sur `.main-content`, `clientWidth: 316px`/390px — bande morte confirmée par capture |
| Positions | 390×844 | Carte affichant `ETHUSD / 24/09/2026 / 1.00000000 / $3100... / $3050... / Kraken` sans aucun libellé, confirmé par capture |
| Trading | 390×844 | Toolbar `scrollWidth: 374px` vs conteneur `clientWidth: 284px` → boutons "4h"/"1D" hors champ, barre de défilement horizontale visible sur capture |

---

## 2. Architecture concrète retenue

### 2.1 Corriger le bug de marge du menu fermé *(priorité absolue)*

Sur mobile, quand `.side-menu` a la classe `hidden` : `.main-content` doit avoir `margin-left: 0`, pas `64px`. Le bouton `.menu-toggle` reste `position: fixed` et flotte par-dessus le contenu (comportement déjà correct), sans qu'aucun espace ne soit réservé dans le flux. Seul le state "ouvert" doit pousser à `translateX` complet du drawer + overlay (`body::before`, déjà en place) par-dessus le contenu — jamais de push de layout, drawer = calque, pas colonne.

### 2.2 Compléter le balisage `data-label` manquant

Ajouter `data-label="..."` sur chaque `<td>` de :
- `apps/investment/templates/investment/investment.html`
- `apps/positions/templates/positions/positions.html`
- `apps/live_trading/templates/live_trading/live_trading.html` (tableau positions ouvertes ET son rendu JS équivalent `renderRow()` — les deux doivent rester synchronisés, sinon le rafraîchissement par polling (`refreshPositions`, toutes les 30s) réintroduit des cartes sans libellé après le premier rendu serveur correct).

### 2.3 Nouveau composant : barre de navigation basse (bottom tab bar)

Remplace la dépendance systématique au drawer pour naviguer entre les sections les plus utilisées. Sur mobile uniquement (`≤599px`) :
- Barre fixe en bas d'écran (`position: fixed; bottom: 0`), 4-5 entrées avec icône + libellé court : **Dashboard, Positions, Trading, Journal, Menu** (le 5e élément "Menu" ouvre le drawer existant pour Analytics/Investissements/Paramètres/Coaching, moins consultés au quotidien selon le cadrage produit — trading actif + suivi des positions sont le cœur d'usage).
- Le bouton hamburger `.menu-toggle` actuel (en haut à gauche) devient redondant avec l'item "Menu" de la tab bar — à supprimer sur mobile une fois la tab bar en place, pour ne pas dupliquer l'accès au drawer.
- `.main-content` doit prévoir un `padding-bottom` suffisant pour ne jamais faire chevaucher la tab bar avec le contenu (notamment le bouton "Ouvrir la position" du ticket Trading, ou les boutons d'action en bas de formulaire modal).
- Fichiers concernés : nouveau `components/bottom-tab-bar.html` (inclus dans le même bloc que `components/side-menu.html`), nouvelles règles dans `static/css/side-menu.css` (ou un nouveau `static/css/bottom-tab-bar.css` si on veut garder la séparation de responsabilités du projet).

### 2.4 Page Trading mobile : toolbar, hauteurs de graphique, action collante

- `.trading-chart-toolbar` : `flex-wrap: wrap` sur mobile, avec le sélecteur d'actif et les boutons d'intervalle qui passent sur 2 lignes si besoin plutôt que de déborder.
- Hauteur de graphique réduite sur mobile (ex. `~260px` prix + `~70px` volume au lieu de `480+120`), pilotée par une détection de largeur (le code utilise déjà `ResizeObserver` pour la largeur — étendre à la hauteur via une constante calculée selon `window.innerWidth` au chargement, cohérent avec le reste du code qui est en vanilla JS sans framework, conformément à `.ai/project-rules.md`).
- **Nouveau composant (optionnel, à valider après tests visuels)** : barre d'action collante en bas du ticket (quantité + bouton "Ouvrir la position" toujours visible pendant qu'on ajuste TP/SL sur le graphique), plutôt que de faire remonter l'utilisateur en haut du formulaire à chaque fois. À n'implémenter que si la vérification visuelle confirme que le parcours actuel est réellement pénible sur petit écran — pas une certitude à ce stade, juste une hypothèse de conception.

### 2.5 Nouveau composant (optionnel) : sélecteur d'actif plein écran

Remplacer le `<select id="assetSelect">` natif par une popup plein écran avec recherche/filtre, plus confortable au doigt qu'un `<select>` HTML natif compressé dans une toolbar déjà chargée. À considérer seulement si le nombre d'actifs suivis grandit (aujourd'hui limité à `DEFAULT_TRADING_SYMBOLS` + actifs suivis de l'utilisateur, donc probablement encore gérable en `<select>` natif) — **non prioritaire**, à ne pas construire avant d'avoir confirmé le besoin.

---

## 3. Missions découpées et priorisées

### M1 — Corriger le bug de marge du menu fermé *(bloquant, cause racine confirmée dans le code)*
- Fichier : `static/css/style.css` (bloc `@media (max-width: 768px)`, à migrer vers `≤599px` après M1 du doc tablette).
- Remplacer `margin-left: var(--sidebar-collapsed-width)` par `margin-left: 0` pour l'état "menu caché" en mobile ; garder le comportement drawer/overlay pour l'état "ouvert".
- Vérifier qu'aucune régression n'apparaît sur le bouton `.menu-toggle` (déjà en `position: fixed`, ne dépend pas du flow).

### M2 — Compléter `data-label` sur les 3 pages manquantes *(bloquant, fort impact/faible effort)*
- `apps/investment/templates/investment/investment.html`, `apps/positions/templates/positions/positions.html`, `apps/live_trading/templates/live_trading/live_trading.html` (template ET fonction JS `renderRow()`).

### M3 — Barre de navigation basse (nouveau composant) *(non-bloquant mais fort gain UX, cohérent avec l'autorisation de créer de nouveaux composants)*
- `components/bottom-tab-bar.html`, CSS associé, suppression du `.menu-toggle` en doublon sur mobile, ajustement `padding-bottom` de `.main-content`.

### M4 — Page Trading mobile : toolbar + hauteurs de graphique adaptatives
- `static/css/trading.css` (`flex-wrap`), `apps/live_trading/templates/live_trading/live_trading.html` (hauteurs JS des charts).

### M5 — Vérification zone paysage (600–900px)
- Pas un développement à proprement parler : une passe de test dédiée (voir section 4) pour confirmer que le mode tablette (rail + colonnes masquées, cf. doc tablette) reste correct en paysage téléphone, et ajuster si besoin (ex. rail encore trop large sur 600-650px de haut en paysage court).

### M6 — Barre d'action collante + sélecteur d'actif plein écran *(optionnel, conditionné aux tests visuels — voir 2.4/2.5)*

---

## 4. Niveaux de test requis (palier Standard)

Comme pour la partie tablette, aucun test Python pertinent — vérification manuelle requise :

1. Chrome + extension Claude in Chrome connectés (bloquant, voir statut en tête de doc).
2. Résolutions à couvrir : `375×667` (iPhone SE/petit), `390×844` (iPhone standard), `412×915` (Android standard), et **paysage** `844×390` / `915×412` pour la vérification M5.
3. Pour chaque page : vérifier absence de scroll horizontal, vérifier que les cartes de tableau affichent bien un libellé par valeur (M2), vérifier que la tab bar (M3) ne recouvre jamais un élément interactif (notamment le bouton de soumission du ticket Trading et les boutons d'action des modales).
4. Vérifier le drawer : ouverture/fermeture, absence de marge résiduelle quand fermé (M1), fermeture au clic sur un lien du menu (comportement déjà existant à ne pas casser).
5. Test tactile explicite sur la page Trading : glisser-déposer des lignes TP/SL (Maj+glissé sur desktop — **à vérifier si un équivalent tactile est nécessaire sur mobile**, voir point en suspens ci-dessous), scroll horizontal manuel du bandeau Vigil.
6. Après implémentation, mettre à jour `.ai/change-log.md`.

---

## 5. Points à signaler avant implémentation

- ✅ Vérification visuelle effectuée (voir 1.5) — bugs de marge du menu, d'étiquettes manquantes et de débordement de la toolbar Trading confirmés par mesure DOM réelle et capture d'écran, pas seulement déduits du code.
- ⚠️ **Limite méthodologique à connaître** : le redimensionnement réel de la fenêtre Chrome (`resize_window`) ne fonctionnait pas dans cette session (fenêtre restée bloquée à 1920px de large quelle que soit la demande, probablement lié à l'environnement d'exécution). Les mesures ont été prises via une **iframe de taille fixe** injectée dans une page same-origin (contournement technique, cookies de session partagés donc authentification correcte), ce qui reproduit fidèlement les media queries CSS et `window.innerWidth`/`scrollWidth` mais **pas** les contraintes d'un vrai navigateur mobile (barre d'adresse rétractable, clavier virtuel, gestes tactiles natifs). Une vérification sur appareil physique ou émulateur Chrome DevTools reste recommandée avant mise en prod — en particulier pour valider M3 (tab bar tactile) et le point en suspens ci-dessous sur le geste TP/SL.
- ❓ **Décision non tranchée, à trancher avant M4/M6** : le geste de déplacement des lignes TP/SL sur le graphique Trading utilise `Maj + clic-glissé` sur desktop (`live_trading.html:543-560`, `event.shiftKey`). **Il n'existe pas d'équivalent tactile pour mobile** (pas de touche Maj sur un écran tactile) — sur mobile, il est donc aujourd'hui impossible de déplacer TP/SL directement sur le graphique ; seule la saisie via les champs du formulaire fonctionne. C'est peut-être acceptable (la saisie manuelle reste possible) mais mérite d'être tranché explicitement : soit on assume que le drag-graphique est une fonctionnalité desktop uniquement (documenter ce choix), soit on prévoit un geste tactile alternatif (ex. long-press sur la ligne) — ce dernier serait un chantier interaction distinct, hors périmètre visuel de ce plan responsive.
- Le contenu exact de la barre de navigation basse (M3 — quelles 5 entrées, quel ordre) est une proposition initiale fondée sur le cadrage produit actuel (`.ai/project-context.md`) ; à confirmer rapidement avec l'utilisateur avant implémentation plutôt qu'à mi-chantier.
- M6 (barre d'action collante, sélecteur plein écran) est délibérément marqué optionnel/conditionnel : ce sont des hypothèses de confort UX non confirmées par un usage réel signalé, à ne construire qu'après validation visuelle du besoin — cohérent avec la règle du projet d'éviter la sur-ingénierie (cf. décision "Table/page dédiée aux news Vigil" rejetée le 2026-09-25 dans `.ai/decisions.md` pour un raisonnement similaire).
