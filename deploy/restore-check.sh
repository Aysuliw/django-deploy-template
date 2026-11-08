#!/usr/bin/env bash
# A backup you have never restored is a hope, not a backup.
# Restores one encrypted dump into a throwaway PostgreSQL container and checks it.
# Run it on your own machine, where the age private key lives:
#   deploy/restore-check.sh app_2026-11-08T03-15-00Z.dump.age ~/.config/age/backup-key.txt
set -euo pipefail
dump="${1:?usage: restore-check.sh <file.dump.age> <age identity file>}"
key="${2:?usage: restore-check.sh <file.dump.age> <age identity file>}"
name="restore-check-$$"

cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$name" -e POSTGRES_PASSWORD=check postgres:16 >/dev/null
until docker exec "$name" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
docker exec "$name" createdb -U postgres restored

age -d -i "$key" "$dump" \
  | docker exec -i "$name" pg_restore -U postgres -d restored --no-owner --exit-on-error

q() { docker exec "$name" psql -U postgres -d restored -tAc "$1"; }
tables=$(q "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
migrations=$(q "SELECT count(*) FROM django_migrations")
echo "restored: $tables tables, $migrations applied migrations"
[[ "$tables" -gt 0 && "$migrations" -gt 0 ]] || { echo "restore check FAILED"; exit 1; }
echo "restore check ok"
