#!/usr/bin/env python3
"""
只读检查疑似重复作者：三个平台的同名、跨平台同名及清理后的相同主页链接。
相同链接是强线索，同名仅供人工判断；不联网、不合并、不修改数据库或 ID。
用法: python find-duplicate-authors.py [--db-path PATH]
"""

import os
import sqlite3
from collections import defaultdict
from pathlib import Path


def _load_env(env_file):
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip()
    except OSError:
        pass


_project_root = Path(
    os.environ.get("PROJECT_ROOT", str(Path(__file__).parent.parent.parent))
)
_load_env(_project_root / ".env")
_project_root = Path(os.environ.get("PROJECT_ROOT", str(_project_root)))

DB_PATH = _project_root / "backend" / "random-2hu-stuff.db"


NAME_COLUMNS = ("yt_name", "nico_name", "twitter_name")
URL_COLUMNS = ("yt_url", "nico_url", "twitter_url")


def normalized_name(value):
    """Ignore whitespace noise and Unicode composition, preserving name case."""
    import unicodedata

    return " ".join(unicodedata.normalize("NFC", value or "").split())


def find_duplicates(con):
    """Return distinct author pairs with direct evidence; no transitive merging."""
    from itertools import combinations

    from author_links import normalize_profile_url

    authors = {}
    name_index = defaultdict(lambda: defaultdict(set))
    url_index = defaultdict(lambda: defaultdict(set))
    canonical_urls = defaultdict(dict)
    invalid_urls = []
    columns = ("id",) + NAME_COLUMNS + URL_COLUMNS
    for values in con.execute(f"SELECT {', '.join(columns)} FROM authors ORDER BY id"):
        author = dict(zip(columns, values))
        author_id = author["id"]
        authors[author_id] = author
        if author_id == 0:
            continue
        for column in NAME_COLUMNS:
            name = normalized_name(author[column])
            if name and name != "原作者未知":
                name_index[name][author_id].add(column)
        for column in URL_COLUMNS:
            value = author[column]
            if not value or not value.strip():
                continue
            normalized = normalize_profile_url(value)
            if normalized is None or normalized[0] != column:
                invalid_urls.append((author_id, column, value))
                continue
            field, url = normalized
            # Twitter usernames are case-insensitive; preserve YouTube path case.
            key = url.lower() if field == "twitter_url" else url
            canonical_urls[author_id][field] = key
            url_index[(field, key)][author_id].add(column)

    matches = defaultdict(lambda: {"urls": [], "names": [], "conflicts": []})
    for (column, url), entries in url_index.items():
        for pair in combinations(sorted(entries), 2):
            matches[pair]["urls"].append(f"{column}: {url}")
    for name, entries in name_index.items():
        for old, new in combinations(sorted(entries), 2):
            matches[(old, new)]["names"].append(
                f"{name!r}: {','.join(sorted(entries[old]))} ↔ {','.join(sorted(entries[new]))}"
            )
    for (old, new), evidence in matches.items():
        for column in URL_COLUMNS:
            a = canonical_urls[old].get(column)
            b = canonical_urls[new].get(column)
            if a and b and a != b:
                evidence["conflicts"].append(f"{column}: {a} ≠ {b}")
    return authors, dict(matches), invalid_urls


def print_author(author):
    print(f"    id={author['id']}")
    for column in NAME_COLUMNS + URL_COLUMNS:
        if author[column]:
            print(f"      {column}: {author[column]}")


def report(con):
    authors, matches, invalid_urls = find_duplicates(con)
    strong = sum(bool(evidence["urls"]) for evidence in matches.values())
    print(f"相同主页链接（强线索）: {strong} 对")
    print(f"仅同名（疑似重复）: {len(matches) - strong} 对")
    print("同名不能证明是同一作者；不同主页可能是小号，也可能是同名作者。")
    for pair, evidence in sorted(
        matches.items(), key=lambda item: (not bool(item[1]["urls"]), item[0])
    ):
        label = "相同主页链接" if evidence["urls"] else "同名，需人工确认"
        print(f"\n[{label}] 作者 {pair[0]} / {pair[1]}")
        for reason in evidence["urls"] + evidence["names"]:
            print(f"  匹配: {reason}")
        for conflict in evidence["conflicts"]:
            print(f"  不同主页: {conflict}")
        for author_id in pair:
            print_author(authors[author_id])
    if invalid_urls:
        print(f"\n未参与链接匹配的非标准/平台不符链接: {len(invalid_urls)} 条")
        for author_id, column, url in invalid_urls:
            print(f"  id={author_id} {column}: {url}")
    print(f"\n合计: {len(matches)} 对候选重复作者（每对只报告一次）。数据库未修改。")
    return matches


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path", type=Path, default=DB_PATH, help="只读检查的数据库路径"
    )
    args = parser.parse_args()
    try:
        con = sqlite3.connect(args.db_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            con.execute("PRAGMA query_only = ON")
            report(con)
        finally:
            con.close()
    except (sqlite3.Error, OSError) as exc:
        print(f"检查失败: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
