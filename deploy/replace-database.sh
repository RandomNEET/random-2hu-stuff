#!/usr/bin/env bash
# Called by upload.sh database-only after uploading a consistent SQLite snapshot.
set -euo pipefail
CANDIDATE="${1:?Uploaded database path required}"
BACKEND_DIR="${DATABASE_BACKEND_DIR:-/var/www/random-2hu-stuff/backend}"
PM2_APP_NAME="${PM2_APP_NAME:-r2s-api}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:3000/health}"
DATABASE="$BACKEND_DIR/random-2hu-stuff.db"
[[ $CANDIDATE == "$BACKEND_DIR"/.database-upload.* ]] || {
  echo 'Unexpected upload path' >&2
  exit 1
}
for tool in python3 pm2 curl; do command -v "$tool" >/dev/null; done
[[ -f $DATABASE && -f $CANDIDATE ]] || {
  echo 'Existing and uploaded databases required' >&2
  exit 1
}
trap 'rm -f -- "$CANDIDATE" "$CANDIDATE-wal" "$CANDIDATE-shm"' EXIT
pm2 describe "$PM2_APP_NAME" >/dev/null
# Reject damaged files or incompatible schemas before stopping the current app.
python3 - "$CANDIDATE" <<'PY'
from pathlib import Path
import sqlite3, sys
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + '?mode=ro', uri=True) as db:
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise SystemExit('Uploaded database integrity check failed')
    for table, fields in {
        'authors': 'id yt_name yt_url yt_avatar nico_name nico_url nico_avatar twitter_name twitter_url twitter_avatar comment',
        'videos': 'id author original_name original_url original_thumbnail original_duration date repost_name repost_url repost_thumbnail repost_duration translation_status comment',
    }.items():
        columns = {row[1] for row in db.execute(f'PRAGMA table_info({table})')}
        if not set(fields.split()) <= columns:
            raise SystemExit(f'Uploaded database missing required columns in {table}')
PY
BACKUP="${DATABASE}.backup.$(date +%Y%m%d-%H%M%S).$$"
STOPPED=0
REPLACED=0
DONE=0
cleanup() {
  local status=$?
  trap - EXIT
  if [[ $DONE == 0 && $STOPPED == 1 ]]; then
    if [[ $REPLACED == 1 ]]; then
      pm2 stop "$PM2_APP_NAME" >/dev/null || true
      rm -f -- "$DATABASE-wal" "$DATABASE-shm"
      cp -p -- "$BACKUP" "$DATABASE" || {
        echo "Restore failed. Backup: $BACKUP" >&2
        exit 1
      }
    fi
    pm2 restart "$PM2_APP_NAME" || true
  fi
  rm -f -- "$CANDIDATE" "$CANDIDATE-wal" "$CANDIDATE-shm"
  exit "$status"
}
trap cleanup EXIT
# Preserve database ownership and mode when switching files.
chmod --reference="$DATABASE" "$CANDIDATE"
chown --reference="$DATABASE" "$CANDIDATE"
pm2 stop "$PM2_APP_NAME"
STOPPED=1
# SQLite backup includes committed WAL content, unlike copying the main file.
python3 - "$DATABASE" "$BACKUP" <<'PY'
from pathlib import Path
import sqlite3, sys
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + '?mode=ro', uri=True) as source:
    with sqlite3.connect(sys.argv[2]) as target:
        source.backup(target)
PY
chmod --reference="$DATABASE" "$BACKUP"
chown --reference="$DATABASE" "$BACKUP"
# At this point the app is stopped; no old sidecars may accompany the new file.
# Mark the switch before touching sidecars so failures restore the full backup.
REPLACED=1
rm -f -- "$DATABASE-wal" "$DATABASE-shm"
mv -f -- "$CANDIDATE" "$DATABASE"
pm2 restart "$PM2_APP_NAME"
for attempt in {1..15}; do
  if curl --max-time 2 -fsS "$HEALTH_URL" >/dev/null; then
    DONE=1
    echo "Database updated. Previous database backup: $BACKUP"
    exit 0
  fi
  sleep 1
done
echo "Health check failed; restoring previous database from $BACKUP" >&2
exit 1
