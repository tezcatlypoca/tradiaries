# Tradiaries — Décisions

**Dernière mise à jour** : 2026-09-12

## Décisions retenues ✅

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

## Décisions en suspens ⏳
- **Question** : Afficher `strategy` dans la table futures_trading.html ?
- **Current** : Champ exists en DB, importé de Notion, affiché en journal/analytics
- **Options** :
  - A) Ajouter colonne dans table futures (encombre l'affichage)
  - B) Garder en détail modal seulement (vue dégradée)
  - C) Responsive : masquer en mobile, afficher en desktop
- **Décision** : À valider par utilisation

### Messages Django pages analytics/journal
- **Question** : Afficher les messages (`{% if messages %}`) ?
- **Current** : Seulement investment.html les affiche
- **Options** :
  - A) Ajouter sur toutes les pages (consistency)
  - B) Garder seulement investment (messages peu pertinents ailleurs)
- **Décision** : À valider

### Déploiement production
- **Question** : Quand basculer en production ?
- **Blocages** :
  - Logo/icônes généré
  - PWA tested iOS/Android
  - Kraken LIVE avec ordre réel (test)
  - Watcher heartbeat validé
- **Risques** :
  - LIVE trading = argent réel
  - Nonce counter DB critique
  - Railway worker availability
- **Décision** : Après test complet PWA + Kraken LIVE limité

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
