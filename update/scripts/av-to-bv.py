#!/usr/bin/env python3
"""
Convert bilibili AV-format repost_url to BV-format.
Creates a timestamped backup before making any changes.

Usage:
  python3 convert-av-to-bv.py [--dry-run]
"""

import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "backend" / "random-2hu-stuff.db"

TABLE = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
S = [11, 10, 3, 8, 4, 6]
XOR = 177451812
ADD = 8728348608


def av_to_bv(av: int) -> str:
    num = (av ^ XOR) + ADD
    bv = ["B", "V", "1", "", "", "4", "", "1", "", "7", "", ""]
    for i in range(6):
        bv[S[i]] = TABLE[num // 58**i % 58]
    return "".join(bv)


def convert_url(url: str) -> str:
    m = re.match(r"(https://www\.bilibili\.com/video/)av(\d+)/?(.*)", url)
    if not m:
        return url
    prefix, av_str, suffix = m.groups()
    try:
        bv = av_to_bv(int(av_str))
    except (ValueError, OverflowError):
        return url
    return f"{prefix}{bv}{'/' if suffix else ''}{suffix}"


def main():
    dry_run = "--dry-run" in sys.argv

    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.stem}_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")
    if dry_run:
        print("(Dry run — database will not be modified)\n")

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro" if dry_run else DB_PATH, uri=dry_run)
    cur = con.cursor()

    rows = cur.execute(
        "SELECT id, repost_url FROM videos "
        "WHERE repost_url LIKE '%/av%' AND repost_url IS NOT NULL AND repost_url != ''"
    ).fetchall()

    print(f"Rows with AV-format URL: {len(rows)}\n")

    to_update = []
    skipped = 0
    for vid_id, url in rows:
        new_url = convert_url(url)
        if new_url != url:
            to_update.append((vid_id, url, new_url))
            print(f"  [{vid_id}] {url}")
            print(f"       → {new_url}")
        else:
            skipped += 1
            print(f"  [{vid_id}] {url}  (no match, skipped)")

    print(f"\nConvertible: {len(to_update)}, Skipped: {skipped}")

    if dry_run or not to_update:
        if not to_update:
            print("Nothing to update.")
    else:
        for vid_id, old_url, new_url in to_update:
            cur.execute("UPDATE videos SET repost_url = ? WHERE id = ?", (new_url, vid_id))
        con.commit()
        print(f"Updated {len(to_update)} rows.")

    con.close()


if __name__ == "__main__":
    main()
