#!/usr/bin/env python3
"""
Find authors that share the same name across different ids, covering:
  1. Same yt_name among multiple authors
  2. Same nico_name among multiple authors
  3. A yt_name of one author matches the nico_name of another author
Read-only: does not modify the database.
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "backend" / "random-2hu-stuff.db"


def find_same_column_dups(con, column):
    """Authors sharing the same value in a single column."""
    rows = con.execute(
        f"""
        SELECT {column}, GROUP_CONCAT(id ORDER BY id) AS ids, COUNT(*) AS cnt
        FROM authors
        WHERE {column} IS NOT NULL AND {column} != ''
        GROUP BY {column}
        HAVING cnt > 1
        ORDER BY {column}
        """
    ).fetchall()
    return rows


def find_cross_column_dups(con):
    """Authors where one's yt_name matches another's nico_name (different ids)."""
    rows = con.execute(
        """
        SELECT a.id AS yt_id, b.id AS nico_id, a.yt_name AS shared_name
        FROM authors a
        JOIN authors b ON a.yt_name = b.nico_name AND a.id != b.id
        WHERE a.yt_name IS NOT NULL AND a.yt_name != ''
        ORDER BY shared_name, yt_id, nico_id
        """
    ).fetchall()
    # Group by shared_name, collect unique id sets
    groups = defaultdict(set)
    for yt_id, nico_id, name in rows:
        groups[name].add(yt_id)
        groups[name].add(nico_id)
    return groups  # {name: {id, ...}}


def fetch_authors_by_ids(con, ids):
    placeholders = ",".join("?" * len(ids))
    return con.execute(
        f"SELECT id, yt_name, yt_url, nico_name, nico_url, twitter_name, twitter_url "
        f"FROM authors WHERE id IN ({placeholders}) ORDER BY id",
        list(ids),
    ).fetchall()


def print_author(a):
    id_, yt_name, yt_url, nico_name, nico_url, tw_name, tw_url = a
    print(f"    id={id_}")
    if yt_name:
        print(f"      yt_name   : {yt_name}")
    if yt_url:
        print(f"      yt_url    : {yt_url}")
    if nico_name:
        print(f"      nico_name : {nico_name}")
    if nico_url:
        print(f"      nico_url  : {nico_url}")
    if tw_name:
        print(f"      twitter   : {tw_name}  {tw_url or ''}")


def main():
    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}")
        return

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    yt_dups = find_same_column_dups(con, "yt_name")
    nico_dups = find_same_column_dups(con, "nico_name")
    cross_dups = find_cross_column_dups(con)

    # ── 1. yt_name 内部重复 ──────────────────────────────────────
    print("=" * 60)
    print(f"1. 重复 yt_name 组: {len(yt_dups)} 个")
    print("=" * 60)
    for name, ids_str, cnt in yt_dups:
        ids = [int(i) for i in ids_str.split(",")]
        print(f"\n  yt_name: 「{name}」")
        for a in fetch_authors_by_ids(con, ids):
            print_author(a)

    # ── 2. nico_name 内部重复 ────────────────────────────────────
    print()
    print("=" * 60)
    print(f"2. 重复 nico_name 组: {len(nico_dups)} 个")
    print("=" * 60)
    for name, ids_str, cnt in nico_dups:
        ids = [int(i) for i in ids_str.split(",")]
        print(f"\n  nico_name: 「{name}」")
        for a in fetch_authors_by_ids(con, ids):
            print_author(a)

    # ── 3. yt_name ↔ nico_name 跨列重复 ─────────────────────────
    print()
    print("=" * 60)
    print(f"3. yt_name 与 nico_name 跨列相同组: {len(cross_dups)} 个")
    print("=" * 60)
    for name, ids in sorted(cross_dups.items()):
        print(f"\n  共同名称: 「{name}」")
        for a in fetch_authors_by_ids(con, sorted(ids)):
            print_author(a)

    print()
    print("=" * 60)
    print(f"合计: {len(yt_dups)} 组 yt_name 重复 + {len(nico_dups)} 组 nico_name 重复 + {len(cross_dups)} 组跨列重复")

    con.close()


if __name__ == "__main__":
    main()
