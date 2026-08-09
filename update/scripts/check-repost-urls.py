#!/usr/bin/env python3
"""
Check whether bilibili repost_url entries are still valid.
Queries the Bilibili API and reports videos that are deleted,
private, or otherwise unavailable.

Usage:
  python3 check-repost-urls.py [--db-path PATH] [--from-id N] [--to-id N] [-o OUTPUT.csv]
"""

import argparse
import csv
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

DB_PATH = Path(__file__).resolve().parent.parent.parent / "backend" / "random-2hu-stuff.db"
LOG_DIR = Path(__file__).resolve().parent

API_UA = "Mozilla/5.0 (compatible; check-repost-urls/1.0)"

GONE_CODES = {
    -404: "不存在",
    62002: "稿件不可见",
    62004: "稿件审核中",
    62006: "稿件已删除",
}


def check(url: str) -> tuple[bool, str]:
    """Returns (ok, message)."""
    # Extract BV or AV from the URL
    m_bv = re.search(r"bilibili\.com/video/(BV[a-zA-Z0-9]+)", url)
    m_av = re.search(r"bilibili\.com/video/av(\d+)", url)
    if m_bv:
        param = f"bvid={m_bv.group(1)}"
    elif m_av:
        param = f"aid={m_av.group(1)}"
    else:
        return True, ""

    try:
        resp = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?{param}",
            headers={"User-Agent": API_UA},
            timeout=10,
        )
        data = resp.json()
        code = data.get("code", -1)
        if code == 0:
            return True, ""
        return False, GONE_CODES.get(code, f"code={code} {data.get('message', '')}")
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--from-id", type=int, default=None)
    parser.add_argument("--to-id", type=int, default=None)
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output CSV path (default: check-repost-urls_TIMESTAMP.csv)",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}")
        sys.exit(1)

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = con.cursor()

    query = (
        "SELECT id, repost_url, original_name FROM videos "
        "WHERE repost_url LIKE '%bilibili.com/video/%' "
        "AND repost_url IS NOT NULL AND repost_url != ''"
    )
    params = []
    if args.from_id is not None:
        query += " AND id >= ?"
        params.append(args.from_id)
    if args.to_id is not None:
        query += " AND id <= ?"
        params.append(args.to_id)
    query += " ORDER BY id"

    rows = cur.execute(query, params).fetchall()
    con.close()

    range_str = ""
    if args.from_id is not None or args.to_id is not None:
        lo = args.from_id if args.from_id is not None else "-"
        hi = args.to_id if args.to_id is not None else "-"
        range_str = f" (id range: {lo}–{hi})"
    print(f"Bilibili repost URLs to check{range_str}: {len(rows)}\n")

    bad_rows = []
    ok = 0
    bad = 0
    n = len(rows)

    for i, (vid_id, url, title) in enumerate(rows):
        valid, msg = check(url)
        idx = i + 1

        if valid:
            ok += 1
            print(f"\r  [{idx}/{n}]  OK: {ok}  Bad: {bad}", end="", flush=True)
        else:
            bad += 1
            print(f"\r  [{idx}/{n}]  OK: {ok}  Bad: {bad}  ✗ [{vid_id}] {title or '(no title)'}")
            print(f"           {url}")
            print(f"           -> {msg}")
            bad_rows.append({
                "id": vid_id,
                "title": title or "",
                "repost_url": url,
                "error": msg,
            })
        time.sleep(0.25)

    print(f"\n\nDone.  OK: {ok},  Bad: {bad}")

    if bad_rows:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = args.output or str(LOG_DIR / f"check-repost-urls_{timestamp}.csv")
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "title", "repost_url", "error"])
            writer.writeheader()
            writer.writerows(bad_rows)
        print(f"Results written: {log_path}")


if __name__ == "__main__":
    main()
