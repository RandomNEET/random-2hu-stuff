#!/usr/bin/env bash
set -euo pipefail

# ---- ssh ----
SSH_HOST="voile"
SSH_USER="howl"
SSH_PORT="22"
SSH_KEY="$HOME/.config/sops-nix/secrets/ssh/voile"
REMOTE_PATH=".vault/rsshub"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COOKIES_FILE="$SCRIPT_DIR/cookies.txt"
DUMP_SCRIPT="$SCRIPT_DIR/dump-cookies.sh"

# ---- 校验 ----
die() {
  echo "ERROR: $*" >&2
  exit 1
}

[ -f "$COOKIES_FILE" ] || die "cookies.txt not found, run export script first"
[ -f "$SSH_KEY" ] || die "SSH key not found: $SSH_KEY"

# ---- 导出 cookies ----
echo "Running $DUMP_SCRIPT ..."
[ -x "$DUMP_SCRIPT" ] || chmod +x "$DUMP_SCRIPT"
"$DUMP_SCRIPT"
[ -f "$COOKIES_FILE" ] || die "cookies.txt still not found after dump"

# ---- 提取 Cookie ----
{
  IFS= read -r sessdata
  IFS= read -r uid
} < <(awk -F'\t' '
    $1 == ".bilibili.com" {
        if ($6 == "SESSDATA")    s = $7
        if ($6 == "DedeUserID")  u = $7
    }
    END { print s""; print u"" }
' "$COOKIES_FILE")

[ -n "$sessdata" ] || die "SESSDATA not found"

LINE="BILIBILI_COOKIE_${uid:-0}=SESSDATA=${sessdata}"
echo "Cookie: ${LINE:0:50}..."

# ---- 上传 ----
echo "Uploading to ${SSH_USER}@${SSH_HOST}:${REMOTE_PATH} ..."

printf '%s\n' "$LINE" | ssh \
  -o StrictHostKeyChecking=accept-new \
  -o ConnectTimeout=10 \
  -o BatchMode=yes \
  -p "$SSH_PORT" \
  -i "$SSH_KEY" \
  "${SSH_USER}@${SSH_HOST}" \
  "mkdir -p '$(dirname "$REMOTE_PATH")' && cat > '$REMOTE_PATH'"

echo "Done."
