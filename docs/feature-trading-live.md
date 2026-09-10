# Feature "Trading Live" — état d'implémentation (2026-09-09)

> **Implémentation terminée et migration BDD appliquée localement.**

## Objectif (validé avec l'utilisateur)

- Passer des ordres **spot réels sur Kraken classic** depuis l'app, avec **TP/SL optionnels**.
- TP/SL gérés **par l'app** (observateur de prix interne qui envoie l'ordre de clôture quand un
  niveau est atteint) — pas d'ordres conditionnels Kraken natifs → compatible **Kraken classic / compte funded**.
- **Nouvelle page dédiée** `/live/` : ouverture de positions **spot ET futures**, chacune en mode
  **PAPER** (rien n'est envoyé à Kraken, BDD locale seule) ou **LIVE** (ordre réel Kraken).
- **Suivi live** des positions ouvertes sur cette page (auto-refresh JS toutes les 30s via endpoint JSON).
- **Popup de validation de la stratégie** (symbole, sens, taille, entrée, TP/SL, R:R, risque $)
  **uniquement pour les ordres LIVE**, avec checklist IRC 4h: au moins 2 critères sur 3 sont requis.
- **Futures LIVE : volontairement NON implémenté** — nécessite l'API Kraken Futures (clés séparées
  de Kraken classic). Garde-fou côté serveur + option désactivée dans l'UI.

## Architecture retenue

```
Formulaire /live/ ──► OpenPositionForm ──► trading_service.open_position()
                                              ├─ PAPER → création BDD locale (prix marché via Ticker public)
                                              └─ LIVE  → kraken_client.add_spot_order() (AddOrder privé)
                                                         + QueryOrders pour le prix de fill réel

Observateur : `python manage.py watch_tp_sl` (boucle, défaut 60s)
    → trading_service.check_tp_sl() → prix Ticker → si TP/SL atteint → close_position()
        ├─ LIVE spot Kraken → ordre de vente market réel
        └─ PAPER → clôture locale au prix courant
```

## Étapes FAITES

### 1. Modèles et migration — [apps/core/models.py](apps/core/models.py)
- `Investment` (abstrait) : + `take_profit`, `stop_loss`, `external_ref` (txid Kraken, unique, null).
- `TRADE_MODES` déplacé de `FuturesTrading` vers `Investment` (partagé).
- `SpotTrading` : + `trade_mode` (PAPER/LIVE, **default PAPER**).
- Migration `0007_futurestrading_external_ref_futurestrading_stop_loss_and_more` appliquée. Elle classe les positions spot historiques en `LIVE` afin qu'elles restent dans le résumé global.

### 2. Stats — [apps/core/portfolio_service.py](apps/core/portfolio_service.py)
- `compute_spot_stats(trade_mode=None)` : filtre optionnel (comme futures).
- `compute_global_stats()` et `build_chart_series()` : spot filtré `LIVE` (paper exclu du résumé global).

### 3. Client Kraken — [apps/core/kraken_client.py](apps/core/kraken_client.py)
- `resolve_pair(symbol)` : résolution paire via AssetPairs public, cache 24h.
- `add_spot_order()` (AddOrder privé, market/limit, validate), `query_orders()`,
  `fetch_order_fill_price()`, `cancel_order()`.

### 4. Service métier — [apps/core/trading_service.py](apps/core/trading_service.py) (nouveau)
- `TradingError`, `open_position()`, `close_position()`, `check_tp_sl()`, `live_positions()`.

### 5. Observateur — [apps/core/management/commands/watch_tp_sl.py](apps/core/management/commands/watch_tp_sl.py) (nouveau)
- `--once` / `--interval` ; setting `TRADING_WATCHER_INTERVAL_SECONDS` (défaut 60) ajouté dans
  [config/settings.py](config/settings.py).

### 6. App `apps/live_trading` (nouvelle)
- [apps.py](apps/live_trading/apps.py), [forms.py](apps/live_trading/forms.py) (`OpenPositionForm`
  + validation cohérence TP/SL vs direction), [urls.py](apps/live_trading/urls.py),
  [views.py](apps/live_trading/views.py) (index / open / close / positions.json),
  template [live_trading.html](apps/live_trading/templates/live_trading/live_trading.html)
  (form modal + **modal validation LIVE** + auto-refresh 30s ; direction & stratégie masqués en spot ;
  option LIVE désactivée en futures).

### 7. Wiring
- `apps.live_trading` dans `INSTALLED_APPS`, route `live/` dans [config/urls.py](config/urls.py),
  lien "⚡ Trading Live" dans [components/side-menu.html](components/side-menu.html),
  CSS dans [static/css/investment.css](static/css/investment.css) (`.investment-action-spot/futures`,
  `.text-positive/negative`, `.tpsl-distance`, `.validation-*`, `.icon-close`).

### 8. Formulaires existants — [apps/core/forms.py](apps/core/forms.py)
- `TradingForm` : + champs `take_profit`/`stop_loss` + validation directionnelle
  (`get_direction()`, spot = LONG ; `FuturesTradingForm` surcharge avec `direction`).
- Les modales spot/futures existantes exposent TP/SL; leurs boutons d'édition les restaurent. La modale spot expose également le mode (LIVE par défaut) et la liste affiche son badge.

### 9. Admin et tests
- L'admin spot/futures expose TP, SL, mode et référence externe.
- Tests: validation TP/SL SHORT, checklist IRC obligatoire en LIVE, ouverture spot PAPER au marché, déclenchement TP, refus futures LIVE et sérialisation de `positions.json` (15 tests ciblés au total).

## Reste à vérifier manuellement

1. **Vérif manuelle** : `python manage.py runserver` → page `/live/`, ouvrir une position PAPER,
   lancer `python manage.py watch_tp_sl --once`, clôturer. Puis test LIVE réel (petit montant).
2. **Clés API Kraken** : vérifier que la clé a la permission **"Create & modify orders"**
   (aujourd'hui lecture seule suffisait pour TradesHistory).

## Points d'attention / décisions

- **Spot = toujours LONG** (achat) ; futures = LONG/SHORT.
- `entry_price` vide dans le form = **ordre market** (live) / prix Ticker courant (paper).
- `external_ref` unique sur `Investment` abstrait → colonne créée dans **les deux** tables
  (spot + futures) ; OK car unique + null.
- Watcher = **processus séparé** à lancer (`watch_tp_sl`) ; sans lui les TP/SL ne se déclenchent pas.
  En cas d'échec de l'ordre de clôture Kraken, la position reste ouverte et sera retentée au cycle suivant.
- Polling page = 30s fixe côté JS ; intervalle watcher affiché depuis `TRADING_WATCHER_INTERVAL_SECONDS`.
- Si la validation JS du R:R n'a pas d'entry_price (market), R:R et risque affichent "-"
  (validation directionnelle TP/SL côté serveur aussi skippée sans entry_price).
