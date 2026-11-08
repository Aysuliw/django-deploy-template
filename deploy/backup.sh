#!/usr/bin/env bash
# Nightly PostgreSQL backup: dump -> encrypt with age -> upload to S3-compatible storage.
# Telegram message if any step fails. Run from cron in the project directory:
#   15 3 * * *  cd /srv/app && deploy/backup.sh >> /var/log/app-backup.log 2>&1
#
# Settings come from /etc/app-backup.env (chmod 600):
#   AGE_RECIPIENT   age public key. The private key is NOT on this server, so a
#                   stolen server can't read old backups.
#   S3_BUCKET, S3_ENDPOINT_URL, S3_PREFIX (default "backups")
#   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
#   KEEP_DAYS       local copies to keep (default 7)
set -euo pipefail

set -a
# shellcheck disable=SC1090,SC1091
. "${BACKUP_ENV:-/etc/app-backup.env}"
set +a
: "${AGE_RECIPIENT:?}" "${S3_BUCKET:?}" "${S3_ENDPOINT_URL:?}"
S3_PREFIX="${S3_PREFIX:-backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
OUT_DIR="${OUT_DIR:-/var/backups/app}"

# shellcheck disable=SC1091
. .env  # DB_NAME and DB_USER, same as the app uses
stamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
file="$OUT_DIR/${DB_NAME}_${stamp}.dump.age"
mkdir -p "$OUT_DIR"

alert() {
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    curl -fsS -m 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id="$TELEGRAM_CHAT_ID" --data-urlencode text="$1" >/dev/null || true
  fi
}
fail() {
  alert "❌ Backup failed: ${DB_NAME} on $(hostname) at ${stamp}. $1"
  rm -f "$file"
  exit 1
}

# Dump straight into age: the unencrypted dump never touches the disk.
docker compose exec -T db pg_dump -U "$DB_USER" -Fc "$DB_NAME" \
  | age -r "$AGE_RECIPIENT" -o "$file" \
  || fail "pg_dump or encryption error"

# A few hundred bytes means pg_dump wrote an error, not a database.
[[ $(stat -c %s "$file") -gt 1024 ]] || fail "backup file is suspiciously small"

aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp --only-show-errors \
  "$file" "s3://${S3_BUCKET}/${S3_PREFIX}/${DB_NAME}/$(basename "$file")" \
  || fail "upload to S3 failed (local copy kept in $OUT_DIR)"

find "$OUT_DIR" -name "${DB_NAME}_*.dump.age" -mtime +"$KEEP_DAYS" -delete
echo "$(date -u +%FT%TZ) backup ok: $(basename "$file")"
