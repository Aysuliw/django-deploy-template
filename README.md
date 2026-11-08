# django-deploy-template

How I put a Django app on a single server: Docker Compose with PostgreSQL, gunicorn and nginx,
safe production settings, error alerts to Telegram, and encrypted backups that are actually
tested by restoring them.

It's deliberately small: one server, no Kubernetes. That's what most small products need,
and it's easy to understand when something breaks at night.

## What's in it

| Piece | File | Why |
|---|---|---|
| Settings from the environment | `config/settings.py` | Refuses to start without `SECRET_KEY`. HTTPS, secure cookies and HSTS when `DEBUG` is off. Passes `manage.py check --deploy`. |
| Health check | `core/views.py` | `/healthz/` returns 503 if the database is unreachable, so monitors and deploys see the real state. |
| Telegram alerts | `core/alerts.py` | Server errors go to a chat, at most once per 5 minutes per error, and a failed alert never breaks a request. |
| App image | `Dockerfile` | Static files collected at build time, runs as a non-root user. |
| The stack | `docker-compose.yml` | Only nginx publishes ports. PostgreSQL is never exposed (Docker bypasses ufw for published ports). |
| nginx | `deploy/nginx.conf` | TLS, HTTP→HTTPS, security headers, static files with caching. |
| Deploy | `deploy/deploy.sh` | Pull, build, migrate, restart, then wait for `/healthz/` to pass. |
| Backups | `deploy/backup.sh` | `pg_dump` streamed straight into [age](https://age-encryption.org) and uploaded to S3-compatible storage. Only the public key is on the server. Telegram message on failure. |
| Restore test | `deploy/restore-check.sh` | Restores a backup into a throwaway PostgreSQL container and checks the tables and migrations are there. |
| Server checklist | `deploy/HARDENING.md` | SSH keys only, firewall, updates, secrets, and what to check if a cryptominer gets in. |

## Run the tests

```bash
docker compose -f docker-compose.dev.yml up -d     # Postgres 16 on port 55434
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DEBUG=1 python manage.py test
```

The tests cover the health check (up and down), the alert handler (sending, cool-down,
never raising) and the production settings (`check --deploy` passes; no `SECRET_KEY`, no start).

## Put it on a server

1. Go through `deploy/HARDENING.md`.
2. Clone the repo to `/srv/app`, copy `.env.example` to `.env` and fill it in (`chmod 600 .env`).
3. Replace `example.com` in `deploy/nginx.conf`, get a certificate with certbot.
4. `deploy/deploy.sh`
5. Backups: create `/etc/app-backup.env`, add `deploy/backup.sh` to cron, and run
   `deploy/restore-check.sh` on your own machine once a month.

## License

MIT
