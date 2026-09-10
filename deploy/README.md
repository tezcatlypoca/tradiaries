# Déploiement Tradiaries

## Watcher TP/SL

Installer `tradiaries-watcher.service` dans `/etc/systemd/system/`, adapter le chemin du projet et créer `/etc/tradiaries/tradiaries.env` avec des permissions `600`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tradiaries-watcher
sudo systemctl status tradiaries-watcher
curl -f https://tradiaries.example.com/healthz/watcher/
```

Le watcher écrit son heartbeat dans `TRADING_WATCHER_HEARTBEAT_FILE`. L'endpoint `/healthz/watcher/` renvoie `503` si le heartbeat est absent ou trop ancien. Configurer une supervision externe sur cet endpoint et sur `/healthz/`.

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

## Secrets et HTTPS

En production, fournir au minimum `SECRET_KEY`, `API_CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, ainsi que les réglages HTTPS. Générer la clé Fernet dédiée avec :

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Ne jamais placer ces valeurs dans Git. Utiliser un reverse proxy HTTPS (Caddy, Traefik ou Nginx) et ne lancer `SECURE_SSL_REDIRECT=True` qu'après validation de `SECURE_PROXY_SSL_HEADER`.
