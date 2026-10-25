#!/usr/bin/env bash
# Debian code deployment. Never copy, delete or change ownership of databases.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DEPLOY_TARGET="${DEPLOY_TARGET:-/var/www/random-2hu-stuff}"
PM2_APP_NAME="${PM2_APP_NAME:-r2s-api}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:3000/health}"
MODE="${1:-all}"
fail() {
  echo "ERROR: $*" >&2
  exit 1
}
check() {
  [[ $EUID == 0 ]] || fail 'Run as root on the Debian server.'
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ $ID == debian ]] || fail 'Deployment supports Debian only.'
  local tool
  for tool in node npm pm2 nginx rsync curl; do command -v "$tool" >/dev/null || fail "Missing: $tool"; done
  node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit((a===20&&b>=19)||(a===22&&b>=12)||a>22?0:1)' || fail 'Node 20.19+ or 22.12+ required.'
  [[ $(realpath -m "$PROJECT_ROOT") != $(realpath -m "$DEPLOY_TARGET") ]] || fail 'Source and deployment directories must differ.'
  nginx -t
  if [[ $MODE != frontend ]]; then
    [[ -f "$DEPLOY_TARGET/backend/random-2hu-stuff.db" ]] || fail 'Existing production database required; initialize it separately.'
    pm2 describe "$PM2_APP_NAME" >/dev/null || fail "Existing PM2 process $PM2_APP_NAME required."
  fi
}
health() {
  local attempt
  for attempt in {1..15}; do
    if curl --max-time 2 -fsS "$HEALTH_URL" >/dev/null; then return; fi
    sleep 1
  done
  fail 'Backend health check failed; inspect PM2 logs. Code backup path was printed above.'
}
case "$MODE" in
all | frontend | backend) ;;
status)
  pm2 describe "$PM2_APP_NAME"
  systemctl is-active nginx
  curl --max-time 5 -fsS "$HEALTH_URL"
  exit
  ;;
*) fail "Usage: $0 [all|frontend|backend|status]. Existing Nginx configuration is preserved." ;;
esac
check
STAGE=$(mktemp -d)
trap 'rm -rf -- "$STAGE"' EXIT
# Finish builds and native dependency installation before changing live files.
if [[ $MODE != backend ]]; then
  (
    cd "$PROJECT_ROOT/frontend"
    npm ci --include=dev
    npm run build
  )
  [[ -f "$PROJECT_ROOT/frontend/dist/index.html" ]] || fail 'Missing built frontend.'
fi
if [[ $MODE != frontend ]]; then
  mkdir -p "$STAGE/backend"
  cp "$PROJECT_ROOT/backend/"{server.cjs,package.json,package-lock.json,ecosystem.config.js} "$STAGE/backend/"
  cp -R "$PROJECT_ROOT/backend/src" "$STAGE/backend/"
  (
    cd "$STAGE/backend"
    npm ci --omit=dev
    node -e 'require("sqlite3");require("./src/app.cjs")'
  )
fi
BACKUP="${BACKUP_ROOT:-/var/backups}/random-2hu-stuff-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$BACKUP"
echo "Code backup: $BACKUP (database excluded)"
if [[ -d "$DEPLOY_TARGET/frontend/dist" ]]; then
  mkdir -p "$BACKUP/frontend"
  cp -a "$DEPLOY_TARGET/frontend/dist" "$BACKUP/frontend/"
fi
if [[ -d "$DEPLOY_TARGET/backend" ]]; then
  mkdir -p "$BACKUP/backend"
  rsync -a --exclude='*.db*' --exclude='node_modules/' --exclude='.env*' "$DEPLOY_TARGET/backend/" "$BACKUP/backend/"
fi
if [[ $MODE != backend ]]; then
  mkdir -p "$DEPLOY_TARGET/frontend/dist"
  # Keep previous hashed assets so already-open pages continue loading chunks.
  rsync -a "$PROJECT_ROOT/frontend/dist/" "$DEPLOY_TARGET/frontend/dist/"
  chmod -R a+rX "$DEPLOY_TARGET/frontend/dist"
fi
if [[ $MODE != frontend ]]; then
  # No --delete at backend root: database, sidecars and runtime files survive.
  rsync -a "$STAGE/backend/" "$DEPLOY_TARGET/backend/"
  pm2 restart "$PM2_APP_NAME"
  health
fi
echo 'Deployment finished. Existing database and Nginx configuration preserved.'
