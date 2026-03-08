#!/usr/bin/env python3
"""
Fix video URLs in the database:
- twitter.com → x.com
- youtube.com/shorts/ID → www.youtube.com/watch?v=ID
Creates a timestamped backup before making any changes.
"""

import sqlite3
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "backend" / "random-2hu-stuff.db"


def fix_url(url):
    if not url:
        return url
    # Twitter → X
    url = re.sub(r'https?://(?:www\.)?twitter\.com/', 'https://x.com/', url)
    # YouTube Shorts → watch URL (strip extra query params like ?si=...)
    m = re.search(r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})', url)
    if m:
        url = f"https://www.youtube.com/watch?v={m.group(1)}"
    return url


def main():
    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}")
        sys.exit(1)

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.stem}_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rows = cur.execute(
        "SELECT id, original_url FROM videos "
        "WHERE original_url LIKE '%twitter.com%' "
        "   OR original_url LIKE '%youtube.com/shorts/%'"
    ).fetchall()

    print(f"Rows to process: {len(rows)}")

    updated = 0
    for vid_id, url in rows:
        new_url = fix_url(url)
        if new_url != url:
            cur.execute("UPDATE videos SET original_url = ? WHERE id = ?", (new_url, vid_id))
            print(f"  [{vid_id}] {url}")
            print(f"       → {new_url}")
            updated += 1

    con.commit()
    con.close()
    print(f"\nDone. Updated {updated} rows.")


if __name__ == "__main__":
    main()
