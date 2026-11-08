#!/usr/bin/env bash
# Deploy the current main branch on the server. Run in the project directory.
# Builds first, migrates, swaps the app container, then checks it is healthy.
set -euo pipefail

git pull --ff-only
docker compose build web
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d --remove-orphans

for _ in $(seq 1 30); do
  if docker compose exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/')" 2>/dev/null; then
    echo "deploy ok: $(git rev-parse --short HEAD)"
    exit 0
  fi
  sleep 2
done
echo "app did not become healthy; see: docker compose logs web" >&2
exit 1
