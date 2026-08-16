#!/usr/bin/env python3
"""
Convert bilibili AV-format repost_url to BV-format.
Queries the Bilibili API for every AV number to get the correct BV.
Falls back to XOR algorithm only if the API fails.

Creates a timestamped backup before making any changes.

Usage:
  python3 av-to-bv.py [--dry-run] [--from-id N] [--to-id N]
"""

import argparse
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "backend" / "random-2hu-stuff.db"
)

TABLE = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
S = [11, 10, 3, 8, 4, 6]
XOR = 177451812
ADD = 8728348608

API_UA = "Mozilla/5.0 (compatible; av-to-bv/1.0)"


def av_to_bv_xor(av: int) -> str:
    num = (av ^ XOR) + ADD
    bv = ["B", "V", "1", "", "", "4", "", "1", "", "7", "", ""]
    for i in range(6):
        bv[S[i]] = TABLE[num // 58**i % 58]
    return "".join(bv)


def av_to_bv_api(av: int) -> str | None:
    try:
        resp = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?aid={av}",
            headers={"User-Agent": API_UA},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None
        return data.get("data", {}).get("bvid")
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-id", type=int, default=None)
    parser.add_argument("--to-id", type=int, default=None)
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.stem}_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")
    if args.dry_run:
        print("(Dry run — database will not be modified)\n")

    con = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro" if args.dry_run else DB_PATH, uri=args.dry_run
    )
    cur = con.cursor()

    query = (
        "SELECT id, repost_url FROM videos "
        "WHERE repost_url LIKE '%/av%' AND repost_url IS NOT NULL AND repost_url != ''"
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
    n = len(rows)

    range_str = ""
    if args.from_id is not None or args.to_id is not None:
        lo = args.from_id if args.from_id is not None else "-"
        hi = args.to_id if args.to_id is not None else "-"
        range_str = f" (id range: {lo}–{hi})"
    print(f"AV-format URLs{range_str}: {n}\n")

    to_update = []
    api_ok = 0
    xor_fallback = 0

    for idx, (vid_id, url) in enumerate(rows):
        m = re.match(r"(https://www\.bilibili\.com/video/)av(\d+)/?(.*)", url)
        if not m:
            continue

        prefix, av_str, suffix = m.groups()
        av = int(av_str)

        bv = av_to_bv_api(av)
        if bv:
            api_ok += 1
            print(
                f"\r  [{idx+1}/{n}]  API:{api_ok}  XOR_fallback:{xor_fallback}",
                end="",
                flush=True,
            )
        else:
            xv = av_to_bv_xor(av)
            xor_fallback += 1
            bv = xv
            print(
                f"\r  [{idx+1}/{n}]  API:{api_ok}  XOR_fallback:{xor_fallback}  ✗ [{vid_id}] av{av} API failed, using XOR: {xv}"
            )

        new_url = (
            f"{prefix}{bv}{'/' if suffix else ''}{suffix}"
            if suffix
            else f"{prefix}{bv}"
        )
        if new_url != url:
            to_update.append((vid_id, url, new_url))

        time.sleep(0.3)

    print(f"\n\nAPI OK: {api_ok},  XOR fallback: {xor_fallback}")
    print(f"To update: {len(to_update)}")

    if to_update:
        print()
        for vid_id, old_url, new_url in to_update:
            xv = av_to_bv_xor(int(re.search(r"av(\d+)", old_url).group(1)))
            bv_new = re.search(r"BV[a-zA-Z0-9]+", new_url).group(0)
            if xv != bv_new:
                print(f"  [{vid_id}] {old_url}")
                print(f"       → {new_url}")

    if args.dry_run:
        print("\n(Dry run — database will not be modified)")
    elif not to_update:
        print("Nothing to update.")
    else:
        for vid_id, old_url, new_url in to_update:
            cur.execute(
                "UPDATE videos SET repost_url = ? WHERE id = ?", (new_url, vid_id)
            )
        con.commit()
        print(f"\nUpdated {len(to_update)} rows.")

    con.close()


if __name__ == "__main__":
    main()
