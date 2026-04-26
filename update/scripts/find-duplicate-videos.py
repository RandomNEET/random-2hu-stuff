#!/usr/bin/env python3
"""
Find videos where the combination of (author, original_name) is duplicated
across different ids.
Read-only: does not modify the database.
"""

import os
import sqlite3
from pathlib import Path


def _load_env(env_file):
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip()
    except OSError:
        pass


_project_root = Path(os.environ.get('PROJECT_ROOT', str(Path(__file__).parent.parent.parent)))
_load_env(_project_root / '.env')
_project_root = Path(os.environ.get('PROJECT_ROOT', str(_project_root)))

DB_PATH = _project_root / "backend" / "random-2hu-stuff.db"


def main():
    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}")
        return

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    groups = con.execute(
        """
        SELECT author, original_name, GROUP_CONCAT(id ORDER BY id) AS ids, COUNT(*) AS cnt
        FROM videos
        WHERE original_name IS NOT NULL AND original_name != ''
          AND author IS NOT NULL
        GROUP BY author, original_name
        HAVING cnt > 1
          AND COUNT(DISTINCT COALESCE(original_url, '')) > 1
        ORDER BY author, original_name
        """
    ).fetchall()

    print("=" * 60)
    print(f"(author, original_name) 相同但 original_url 不同的组: {len(groups)} 个")
    print("=" * 60)

    for author_id, orig_name, ids_str, cnt in groups:
        ids = [int(i) for i in ids_str.split(",")]
        placeholders = ",".join("?" * len(ids))
        rows = con.execute(
            f"""
            SELECT v.id, v.author, a.yt_name, a.nico_name,
                   v.original_name, v.original_url,
                   v.repost_name, v.repost_url,
                   v.date, v.translation_status
            FROM videos v
            LEFT JOIN authors a ON v.author = a.id
            WHERE v.id IN ({placeholders})
            ORDER BY v.id
            """,
            ids,
        ).fetchall()

        author_label = f"author={author_id}"
        if rows and (rows[0][2] or rows[0][3]):
            name = rows[0][2] or rows[0][3]
            author_label += f" ({name})"

        print(f"\n  {author_label}  original_name: 「{orig_name}」")
        for r in rows:
            vid_id, _, yt_name, nico_name, o_name, o_url, r_name, r_url, date, status = r
            print(f"    id={vid_id}  date={date}  translation_status={status}")
            if o_url:
                print(f"      original_url : {o_url}")
            if r_name or r_url:
                print(f"      repost       : {r_name or ''}  {r_url or ''}")

    con.close()
    print(f"\n合计: {len(groups)} 组 (author+original_name 相同但 original_url 不同)")


if __name__ == "__main__":
    main()
