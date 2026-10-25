#!/usr/bin/env bash
# Upload code to a separate source directory, then use the Debian deployment entry.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
if [[ -f "$LOCAL_PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$LOCAL_PROJECT_ROOT/.env"
  set +a
fi
MODE="${1:-all}"
case "$MODE" in
build-only)
  (
    cd "$LOCAL_PROJECT_ROOT/frontend"
    npm ci --include=dev
    npm run build
  )
  exit
  ;;
all | upload-only | database-only) ;;
*)
  echo "Usage: $0 [build-only|upload-only|database-only]" >&2
  exit 1
  ;;
esac
: "${REMOTE_SERVER:?Set REMOTE_SERVER (user@host)}"
: "${SSH_KEY:?Set SSH_KEY}"
: "${SSH_PORT:?Set SSH_PORT}"
# This is a source checkout, never the live /var/www application directory.
REMOTE_SOURCE="${REMOTE_SOURCE:-/root/random-2hu-stuff-upload}"
[[ $REMOTE_SOURCE =~ ^/root/[a-zA-Z0-9_-]+$ ]] || {
  echo 'REMOTE_SOURCE must be a directory directly under /root.' >&2
  exit 1
}
for tool in ssh rsync ssh-agent ssh-add; do command -v "$tool" >/dev/null; done
STAGE=$(mktemp -d)
OWN_AGENT=0
cleanup() {
  rm -rf -- "$STAGE"
  if [[ $OWN_AGENT == 1 ]]; then ssh-agent -k >/dev/null; fi
}
trap cleanup EXIT
# Use the current agent when available; only terminate an agent started here.
if [[ -z ${SSH_AUTH_SOCK:-} ]]; then
  eval "$(ssh-agent -s)" >/dev/null
  OWN_AGENT=1
fi
ssh-add "$SSH_KEY"
SSH=(ssh -i "$SSH_KEY" -p "$SSH_PORT")
"${SSH[@]}" "$REMOTE_SERVER" 'test "$(. /etc/os-release; echo "$ID")" = debian && command -v node && command -v npm && command -v pm2 && command -v rsync'
if [[ $MODE == database-only ]]; then
  command -v python3 >/dev/null
  # Snapshot through SQLite so local WAL content is included without uploading sidecars.
  python3 - "$LOCAL_PROJECT_ROOT/backend/random-2hu-stuff.db" "$STAGE/database.db" <<'PYTHON'
from pathlib import Path
import sqlite3, sys
source_path = Path(sys.argv[1]).resolve()
with sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True) as source:
    with sqlite3.connect(sys.argv[2]) as target:
        source.backup(target)
PYTHON
  REMOTE_DATABASE=$("${SSH[@]}" "$REMOTE_SERVER" 'command -v python3 >/dev/null && mktemp /var/www/random-2hu-stuff/backend/.database-upload.XXXXXXXX')
  [[ $REMOTE_DATABASE =~ ^/var/www/random-2hu-stuff/backend/\.database-upload\.[A-Za-z0-9]+$ ]] || {
    echo 'Unexpected remote upload path' >&2
    exit 1
  }
  rsync -rz --progress -e "ssh -p $SSH_PORT" "$STAGE/database.db" "$REMOTE_SERVER:$REMOTE_DATABASE"
  "${SSH[@]}" "$REMOTE_SERVER" "bash -s -- '$REMOTE_DATABASE'" <"$LOCAL_PROJECT_ROOT/deploy/replace-database.sh"
  exit
fi
mkdir -p "$STAGE/frontend" "$STAGE/backend" "$STAGE/deploy"
rsync -a --exclude=node_modules --exclude=dist --exclude='.env*' "$LOCAL_PROJECT_ROOT/frontend/" "$STAGE/frontend/"
cp "$LOCAL_PROJECT_ROOT/backend/"{server.cjs,package.json,package-lock.json,ecosystem.config.js} "$STAGE/backend/"
cp -R "$LOCAL_PROJECT_ROOT/backend/src" "$STAGE/backend/"
cp "$LOCAL_PROJECT_ROOT/deploy/deploy.sh" "$STAGE/deploy/"
"${SSH[@]}" "$REMOTE_SERVER" "mkdir -p '$REMOTE_SOURCE'"
# No database or credentials in the bundle, no deletion in the live directory.
# SSH_KEY is handled by the agent, avoiding shell quoting in rsync's transport.
rsync -rz --progress -e "ssh -p $SSH_PORT" "$STAGE/" "$REMOTE_SERVER:$REMOTE_SOURCE/"
if [[ $MODE == upload-only ]]; then
  echo "Source uploaded. Run on server: bash '$REMOTE_SOURCE/deploy/deploy.sh'"
else
  "${SSH[@]}" "$REMOTE_SERVER" "bash '$REMOTE_SOURCE/deploy/deploy.sh'"
fi
