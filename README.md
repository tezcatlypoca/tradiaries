# Tradiaries

Application Django de suivi d'investissements et de trading.

## Développement

```powershell
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Copier `.env.example` vers `.env`. Le projet utilise SQLite par défaut. Pour PostgreSQL,
définir `DATABASE_URL`, par exemple `postgresql://user:password@localhost:5432/tradiaries`.

## Exploitation

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

L'endpoint `GET /healthz/` vérifie la connexion à la base de données. La synchronisation
Kraken est volontairement hors requête web : elle se lance avec `python manage.py
import_kraken_trades`, à planifier via le système de tâches de l'environnement de production.

En production, définir `DEBUG=False`, une `SECRET_KEY` longue et aléatoire, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS` et les paramètres HTTPS dans l'environnement. Ne jamais journaliser
les clés Kraken.