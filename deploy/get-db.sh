#!/usr/bin/env bash

# Fetch the latest database from DoltHub and export to SQLite
# Usage: ./get-db.sh [output_path]
# Default output: $PROJECT_ROOT/backend/random-2hu-stuff.db

set -e

# Load project root .env if present
_ENV_FILE="${PROJECT_ROOT:-/root/random-2hu-stuff}/.env"
if [[ -f "$_ENV_FILE" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$_ENV_FILE"; set +a
fi

: "${DOLTHUB_REPO:?'DOLTHUB_REPO is not set. Add it to /root/.env'}"
: "${PROJECT_ROOT:=/root/random-2hu-stuff}"

OUTPUT_DB="${1:-$PROJECT_ROOT/backend/random-2hu-stuff.db}"
DOLT_WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$DOLT_WORK_DIR"' EXIT

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

if ! command -v dolt &>/dev/null; then
  log_error "dolt is not installed. Install with:"
  echo "  curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash"
  exit 1
fi

log_info "Cloning $DOLTHUB_REPO from DoltHub..."
dolt clone "$DOLTHUB_REPO" "$DOLT_WORK_DIR/repo"

cd "$DOLT_WORK_DIR/repo"

log_info "Exporting tables to SQLite: $OUTPUT_DB"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_DB")"

# Remove existing database to start fresh
rm -f "$OUTPUT_DB"

# Get list of tables
TABLES=$(dolt sql --result-format=csv -q "SHOW TABLES" | tail -n +2 | tr -d '\r')

# Export each table to CSV
for table in $TABLES; do
  log_info "  Exporting table: $table"
  dolt sql --result-format=csv -q "SELECT * FROM \`$table\`" > "$DOLT_WORK_DIR/${table}.csv"
done

# Use Python to handle CSV → SQLite conversion cleanly
python3 - <<EOF
import csv, sqlite3, os, sys

db_path = "$OUTPUT_DB"
work_dir = "$DOLT_WORK_DIR"
tables = [t.strip() for t in """$TABLES""".strip().splitlines() if t.strip()]

conn = sqlite3.connect(db_path)

# Schema definitions matching the existing backend database exactly
SCHEMAS = {
    "authors": """
        CREATE TABLE "authors" (
            "id"    INTEGER NOT NULL UNIQUE,
            "yt_name"       TEXT,
            "yt_url"        TEXT,
            "yt_avatar"     TEXT,
            "nico_name"     TEXT,
            "nico_url"      TEXT,
            "nico_avatar"   TEXT,
            "twitter_name"  TEXT,
            "twitter_url"   TEXT,
            "twitter_avatar"        TEXT,
            "comment"       TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """,
    "videos": """
        CREATE TABLE "videos" (
            "id"    INTEGER NOT NULL UNIQUE,
            "author"        INTEGER,
            "original_name" TEXT,
            "original_url"  TEXT,
            "original_thumbnail"    TEXT,
            "date"  TEXT,
            "repost_name"   TEXT,
            "repost_url"    TEXT,
            "repost_thumbnail"      TEXT,
            "translation_status"    INTEGER,
            "comment"       TEXT,
            PRIMARY KEY("id" AUTOINCREMENT),
            FOREIGN KEY("author") REFERENCES "authors"("id")
        )
    """,
}

for table in tables:
    csv_file = os.path.join(work_dir, f"{table}.csv")
    if not os.path.exists(csv_file):
        print(f"  Skipping {table}: CSV not found")
        continue

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"  Skipping {table}: no data")
        continue

    # Use predefined schema if available, otherwise infer TEXT columns
    if table in SCHEMAS:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(SCHEMAS[table])
    else:
        cols = ", ".join(f'"{c}" TEXT' for c in rows[0].keys())
        conn.execute(f"DROP TABLE IF EXISTS \"{table}\"")
        conn.execute(f'CREATE TABLE "{table}" ({cols})')

    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(f'"{c}"' for c in cols)

    def coerce(v, col):
        return None if v == "" else v

    data = [tuple(coerce(row[c], c) for c in cols) for row in rows]
    conn.executemany(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})', data)
    print(f"  {table}: {len(data)} rows imported")

conn.commit()
conn.close()
print(f"SQLite database written to: {db_path}")
EOF

log_success "Done! Database saved to: $OUTPUT_DB"
