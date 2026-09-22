# Production Readiness Check — 2026-09-22 (branche `dev`)

**Verdict** : 🟠 READY WITH WARNINGS pour usage Phase 1 (personnel) — 🔴 NOT READY pour toute ouverture à des utilisateurs non explicitement invités.

## Bloquants

### B1 — Travail non commité au moment du check
Migration `core.0017_apicredentialauditlog`, audit trail `ApiCredential`, et toute la suite de tests renforcée (Mission 1-4, voir `docs/testing-plan-2026-09-22.md`) étaient non commités au moment du check. Rien de tout cela n'est déployable tant que non mergé — la migration ne s'appliquera jamais sur Neon sans ça.

### B2 — L'inscription publique contredit la prémisse "invite-only" de la décision de sécurité Fernet
`apps/dashboard/forms.py::SignupForm` : aucune restriction (pas de code d'invitation, pas d'email, pas d'approbation admin). `accounts/signup/` est un endpoint public.

La décision gelée "Gestion des secrets API" (2026-09-22, `decisions.md`) justifie la clé Fernet **unique pour toute l'instance** par : *"suffisante pour un modèle invite-only / petit pool de traders"*, avec bascule explicite prévue *"si ouverture large"*. Le code ne respecte déjà pas cette précondition : n'importe qui peut créer un compte aujourd'hui, sans invitation, et y attacher de vraies clés Kraken LIVE. Une fuite de `SECRET_KEY` compromettrait donc les clés de tous les comptes, y compris ceux créés librement par des inconnus.

**Décision requise** (voir `decisions.md`, "En suspens") : fermer le signup public, ou ajouter un mécanisme d'invitation réel.

## Avertissements (non bloquants Phase 1)

- Pas de protection anti-brute-force sur login/signup (pas de `django-axes`/`ratelimit`/CAPTCHA).
- Pas de monitoring/alerting (Sentry ou équivalent) — déjà identifié comme requis avant Phase 2.
- Bug connu (non corrigé, hors périmètre) : `watch_tp_sl.py` peut mal classer un cycle réussi comme échec sur console Windows (cp1252) — sans impact prod (Railway = Linux/UTF-8).
- `DATABASE_URL` sans `connect_timeout`/`statement_timeout` explicites.

## Ce qui est déjà solide

- `check --deploy` propre, `makemigrations --check` propre, 85/85 tests verts, CI simule un environnement prod réaliste.
- Isolation multi-utilisateur vérifiée par grep exhaustif sur tous les `views.py` — aucune fuite trouvée.
- Les 3 P0 de l'audit précédent (`docs/audit-production.md`, 2026-09-10) sont corrigés : machine d'états `KrakenOrderAttempt`, retry désactivé sur ordres non-idempotents, verrou atomique `is_closing`.
- Déchiffrement Fernet invalide désormais loggé (plus de `''` silencieux).
- Clé Kraken dupliquée : unicité imposée au niveau formulaire (plus de "choix silencieux de la première").
- Aucune injection XSS exploitable trouvée sur les 3 usages de `|safe` (tous du JSON/help_text généré serveur).
