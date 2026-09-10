# Tradiaries — Plan de mise en production

## Niveau 1 — Prod solo (usage personnel)

Objectif : usage fiable en continu, avec de l'argent réel, sans surveillance manuelle.

- [x] **Watcher TP/SL en tâche fiable (socle applicatif livré)**
  - Unité systemd `deploy/tradiaries-watcher.service` avec redémarrage automatique
  - Heartbeat et healthcheck `/healthz/watcher/`
  - Reste à configurer l'alerte externe (Telegram/email) sur le healthcheck
- [ ] **PostgreSQL + backups**
  - Support PostgreSQL déjà présent via `DATABASE_URL`
  - Script de backup `deploy/backup-postgres.sh` avec rétention et empreinte SHA-256
  - Reste à planifier le cron, copier vers un stockage distant et tester une restauration
- [x] **Secrets & HTTPS (configuration prête)**
  - `SECRET_KEY` et `API_CREDENTIAL_ENCRYPTION_KEY` sont contrôlées en production
  - HTTPS, cookies sécurisés, HSTS et proxy HTTPS sont configurables par variables d'environnement
  - Reste à fournir les secrets via vault/env et à installer le reverse proxy
- [x] **Monitoring minimal (endpoints livrés)**
  - `/healthz/` vérifie la base de données
  - `/healthz/watcher/` vérifie la fraîcheur du heartbeat
  - Reste à brancher un uptime checker externe et ses alertes

**Estimation : 3-5 jours de deep work.**

---

## Niveau 2 — Prod multi-utilisateur (SaaS payant)

### Bloquant absolu — sécurité & isolation

> Non traité dans ce lot : le projet reste mono-utilisateur du point de vue des données. Il ne doit pas être ouvert à plusieurs comptes avant l'ajout du rattachement `User` et du filtrage systématique des querysets.

- [ ] Rattacher tous les modèles (`SimpleInvestment`, `SpotTrading`, `FuturesTrading`, `ApiCredential`) à un `User`
- [ ] Permissions objet strictes (django-guardian ou scoping manuel des querysets)
- [ ] Clé de chiffrement des API keys dérivée par utilisateur (pas une clé globale unique)
- [ ] Rate limiting / quotas d'appels Kraken par utilisateur

### Bloquant business — paiement & légal

- [ ] Facturation Stripe Billing (checkout + webhooks + gestion des états d'abonnement)
- [ ] CGU + mentions légales + disclaimer non-conseil financier (obligatoire dès facturation ; faire relire par un avocat ou partir d'un template solide type Termly)
- [ ] Conformité RGPD : suppression de compte/données, export des données, hébergement UE si cible FR/UE

### Infra & fiabilité — scalabilité

- [ ] Celery + Redis pour sortir les syncs Kraken et le watcher TP/SL du serveur web
- [ ] CI/CD basique (GitHub Actions)
- [ ] Tests métier sur le calcul de PnL (critique : erreur de calcul avec argent réel d'un tiers = risque légal/réputation)
- [ ] Gestion d'erreurs Kraken isolée par utilisateur (un rate-limit sur un compte ne doit pas impacter les autres)

### Différenciateur — Coach IA

- [ ] Implémenter le MVP tel que décrit dans `project-overview.md` (briefing avant entrée, revue post-clôture en 5 questions max, synthèse hebdo)
- [ ] Garder les garde-fous : anonymisation des données envoyées au modèle, pas d'envoi de secrets API, signalement des échantillons trop faibles, ton factuel non-culpabilisant
- [ ] Séparer clairement faits / calculs / suggestions générées par le modèle dans l'UI

**Estimation : 6-10 semaines pour une V1 SaaS sérieuse (scope restreint, ex : pas de futures LIVE au lancement).**

---

## Plan d'action

| Horizon | Action |
|---|---|
| **Immédiat** (cette semaine) | Migration PostgreSQL + backup auto + systemd/healthcheck pour le watcher |
| **Court terme** (2-4 semaines) | Multi-tenancy (User FK + permissions objet) + tests sur les calculs de PnL |
| **Moyen terme** (1-3 mois) | Stripe + CGU/disclaimer + Celery + lancement du Coach IA en beta fermée |

---

## Piste à explorer

Séparer le **Coach IA** de Tradiaries pour en faire un produit indépendant (le "Trade Journal Intelligence" du portfolio), connectable à Tradiaries ou à un CSV/API tiers. Élargit le marché sans attendre que Tradiaries soit 100% prod-ready.
