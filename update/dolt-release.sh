#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DB_PATH="${1:-$PROJECT_ROOT/backend/random-2hu-stuff.db}"
DOLT_DIR="${DOLT_DIR:-$PROJECT_ROOT/dolt}"
DOLTHUB_REMOTE="${DOLTHUB_REMOTE:-origin}"
RELEASE_DATE=$(date +%Y%m%d)

if [ ! -f "$DB_PATH" ]; then
  echo "错误: 找不到数据库文件 $DB_PATH"
  exit 1
fi

if [ ! -d "$DOLT_DIR/.dolt" ]; then
  echo "错误: $DOLT_DIR 不是有效的 Dolt 仓库"
  echo "请先执行:"
  echo "  mkdir -p \"$DOLT_DIR\" && cd \"$DOLT_DIR\""
  echo "  dolt init"
  echo "  dolt remote add origin <yourname/random-2hu-stuff>"
  exit 1
fi

echo "==> 从 SQLite 导出表为 CSV ..."
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

python3 - <<EOF
import sqlite3, csv, os

db = sqlite3.connect("$DB_PATH")
db.row_factory = sqlite3.Row
tmpdir = "$TMPDIR"

for table in ("authors", "videos"):
    rows = db.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        continue
    out = os.path.join(tmpdir, f"{table}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        w.writerows(rows)
    print(f"  {table}: {len(rows)} 行 -> {out}")

db.close()
EOF

echo "==> 导入到 Dolt 仓库 $DOLT_DIR ..."
cd "$DOLT_DIR"

# 表存在则 replace (-r)，否则 create (-c)
dolt_import() {
  local table=$1 file=$2
  if dolt ls | grep -qx "$table"; then
    dolt table import -r "$table" "$file"
  else
    dolt table import -c "$table" "$file"
  fi
}

dolt_import authors "$TMPDIR/authors.csv"
dolt_import videos "$TMPDIR/videos.csv"

echo "==> 检查变更 ..."
dolt diff --stat

echo "==> 提交并推送 ..."
dolt add .
dolt commit -m "database update $RELEASE_DATE"
dolt tag "database-$RELEASE_DATE"
dolt push "$DOLTHUB_REMOTE" main
dolt push "$DOLTHUB_REMOTE" "database-$RELEASE_DATE"

echo ""
echo "发布完成！"
REMOTE_URL=$(dolt remote -v 2>/dev/null | awk -v r="$DOLTHUB_REMOTE" '$1==r{print $2; exit}' | sed 's|https://doltremoteapi.dolthub.com/||')
echo "DoltHub 地址: https://www.dolthub.com/repositories/${REMOTE_URL:-<your-repo>}"
echo "克隆命令: dolt clone ${REMOTE_URL:-<yourname/random-2hu-stuff>}"
