# Déploiement Tradiaries

## Watcher TP/SL

Installer `tradiaries-watcher.service` dans `/etc/systemd/system/`, adapter le chemin du projet et créer `/etc/tradiaries/tradiaries.env` avec des permissions `600`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tradiaries-watcher
sudo systemctl status tradiaries-watcher
curl -f https://tradiaries.example.com/healthz/watcher/
```

Le watcher écrit son heartbeat **en base de données** (table `core_watcher_heartbeat`, voir `apps/core/watcher_health.py`) — pas sur disque — car le watcher et le serveur web peuvent tourner sur des machines séparées sans système de fichiers commun (ex. worker Railway + web Render). L'endpoint `/healthz/watcher/` renvoie `503` si le heartbeat est absent ou trop ancien. Configurer une supervision externe sur cet endpoint et sur `/healthz/`.

## Déploiement Render (web) + Railway (worker) + Neon (PostgreSQL)

Topologie gratuite pour un usage personnel : Render héberge l'app web (Gunicorn), Railway exécute `watch_tp_sl` en continu, Neon fournit PostgreSQL. Les deux services (Render et Railway) doivent utiliser **exactement les mêmes variables d'environnement** de sécurité/DB — seule la commande de démarrage change.

### Neon
- Copier la *connection string* "pooled" fournie par Neon (inclut déjà `sslmode=require`) dans `DATABASE_URL`.
- Neon suspend son compute après inactivité : `DB_CONN_MAX_AGE=0` (défaut) évite de réutiliser une connexion devenue invalide après une reprise.

### Render (service web)
- Build Command : `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start Command : `gunicorn config.wsgi:application`
- Filet de sécurité si le Build Command Render ne peut pas être corrigé immédiatement :
  définir `GUNICORN_CMD_ARGS=--config config/gunicorn.py` et
  `RUN_MIGRATIONS_ON_START=True`. Gunicorn applique alors les migrations une fois,
  dans le processus maître, avant d'ouvrir les workers. Une erreur de migration
  bloque volontairement le démarrage plutôt que de servir une application avec un
  schéma incompatible.
- Variables d'environnement : `SECRET_KEY`, `API_CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`, `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_PROXY_SSL_HEADER_ENABLED=True` (Render termine le TLS et transmet `X-Forwarded-Proto`). `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` n'ont pas besoin d'inclure le domaine Render : `RENDER_EXTERNAL_HOSTNAME` (fourni automatiquement par Render) est ajouté automatiquement par `config/settings.py`. Ajouter un domaine perso si utilisé.

### Railway (worker)
- Start Command : `python manage.py watch_tp_sl`
- **Mêmes variables** `SECRET_KEY`, `API_CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`, `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` que sur Render — le garde-fou HTTPS de `config/settings.py` s'applique à tout process qui charge les settings, y compris cette commande sans serveur HTTP.
- `ALLOWED_HOSTS` peut rester la valeur par défaut (ce process ne reçoit aucune requête HTTP).

### Vérifications post-déploiement
- `curl https://<app>.onrender.com/healthz/` → `{"status": "ok"}`
- `curl https://<app>.onrender.com/healthz/watcher/` → `{"status": "ok", "watcher": "running"}` seulement après qu'au moins un cycle du worker Railway se soit exécuté.
- Se créer un compte via `python manage.py createsuperuser` (Render Shell) — aucune inscription publique n'est exposée.

## PostgreSQL

Le serveur doit définir `DATABASE_URL` avec une URL PostgreSQL et exécuter les migrations avant le démarrage de l'application.

Le script `backup-postgres.sh` crée un dump custom et son empreinte SHA-256. Exemple de tâche quotidienne :

```cron
15 2 * * * root DATABASE_URL='postgresql://user:password@host:5432/tradiaries' BACKUP_DIR=/var/backups/tradiaries /opt/tradiaries/deploy/backup-postgres.sh >> /var/log/tradiaries-backup.log 2>&1
```

Copier ensuite les dumps vers un stockage distinct et chiffré (S3, Backblaze ou équivalent). Un backup n'est considéré fiable qu'après un test de restauration sur une base isolée :

```bash
createdb tradiaries_restore_check
pg_restore --clean --if-exists --dbname=tradiaries_restore_check /var/backups/tradiaries/tradiaries-YYYYMMDDTHHMMSSZ.dump
python manage.py migrate --check
 dropdb tradiaries_restore_check
```

Avec Neon : ce cron doit tourner sur une machine tierce (le service gratuit Render/Railway n'a pas de cron natif fiable) — une petite tâche planifiée locale ou un service comme GitHub Actions (cron scheduled workflow) avec `DATABASE_URL` en secret peut suffire pour un usage personnel.

## Secrets et HTTPS

En production, fournir au minimum `SECRET_KEY`, `API_CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, ainsi que les réglages HTTPS. Générer la clé Fernet dédiée avec :

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Ne jamais placer ces valeurs dans Git. Sur Render, le TLS est terminé par la plateforme (`SECURE_PROXY_SSL_HEADER_ENABLED=True` requis) ; en dehors de Render/Railway, utiliser un reverse proxy HTTPS (Caddy, Traefik ou Nginx) et ne lancer `SECURE_SSL_REDIRECT=True` qu'après validation de `SECURE_PROXY_SSL_HEADER`.
