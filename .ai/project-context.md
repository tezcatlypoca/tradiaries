# Tradiaries — Project Context

**Dernière mise à jour** : 2026-09-12  
**État générale** : Fonctionnel en dev, PWA avec icon candlestick, UI bugs corrigés

## Cadrage

**Tradiaries** est une application Django personnelle de suivi de trading et d'investissements en cryptomonnaies. Elle gère :
- Investissements simples (achat/vente USDT)
- Trading spot sur Kraken (LIVE/PAPER)
- Trading futures (LIVE/PAPER) avec journal et analytics
- Suivi du portefeuille via dashboard
- Watcher TP/SL pour gestion automatique des positions

**Stack** : Python 3.11 + Django 5.2 + Vanilla JS + CSS DeFi dark-theme  
**Utilisateurs** : Mono-utilisateur (admin créé via `createsuperuser`)  
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

### À faire ⏳

#### Responsive mobile (< 600px)
- 🟡 Portfolio chart responsive (ajuster hauteur/polices)
- 🟡 Test complet sur vrais appareils (tablette/téléphone)

#### Futures Trading
- 🟡 Affichage du champ `strategy` dans la table futures_trading.html

#### Analytics/Journal
- 🟡 Django messages sur ces pages (actuellement seule investment l'affiche)

#### Déploiement
- 🟡 Test complet Render + Railway + Neon
- 🟡 Vérifications health checks watcher

---

## Problèmes connus

### Résolus cette session (2026-09-12)
- ✅ **Menu replié recouvrait le contenu** → Fixed avec `margin-left: calc(64px - 264px)`
- ✅ **Menu s'ouvrait après clique tabs** → Fixed avec localStorage initial setup sans animation
- ✅ **CSS désorganisé** → Refacto : layout global dans `style.css`, menu styling dans `side-menu.css`
- ✅ **Site blanc** → Fixed : import `style.css` dans tous les templates

### En attente
- ❓ `position: fixed` menu mobile peut pas scrollable si beaucoup de liens (15+ items)
- ❓ Graphique chart pas responsive en très petit (< 300px hauteur)
- ❓ iOS Safari PWA install : valider sur appareil réel (PNG 192/512 en place, test requis)

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
