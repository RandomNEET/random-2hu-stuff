#!/usr/bin/env python3
"""删除全 NULL 作者、连续编号并同步视频关联；修改前自动备份。"""

import argparse
from datetime import datetime
from pathlib import Path
import sqlite3
import sys


DEFAULT_DB = Path(__file__).resolve().parents[2] / "backend/random-2hu-stuff.db"


def connect(path, readonly=False):
    mode = "ro" if readonly else "rw"
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True,
                           timeout=30, isolation_level=None)


def inspect(conn):
    columns = [row[1] for row in conn.execute("PRAGMA table_info(authors)")]
    if "id" not in columns or len(columns) < 2:
        raise RuntimeError("authors 表结构不符合要求")
    authors = conn.execute("SELECT * FROM authors ORDER BY id").fetchall()
    id_index = columns.index("id")
    by_id = {row[id_index]: row for row in authors}
    if 0 not in by_id:
        raise RuntimeError("缺少作者 0（原作者未知）")
    if list(conn.execute("PRAGMA foreign_key_check")):
        raise RuntimeError("数据库已有失效外键关联，请先修复")
    removed = {
        row[id_index] for row in authors
        if row[id_index] != 0
        and all(value is None for i, value in enumerate(row) if i != id_index)
    }
    mapping = {0: 0}
    mapping.update({old: new for new, old in enumerate(
        (old for old in sorted(by_id) if old != 0 and old not in removed), 1)})
    videos = conn.execute("SELECT * FROM videos ORDER BY id").fetchall()
    video_columns = [row[1] for row in conn.execute("PRAGMA table_info(videos)")]
    author_index = video_columns.index("author")
    if any(row[author_index] is not None and row[author_index] not in by_id
           for row in videos):
        raise RuntimeError("videos 中存在失效作者关联，请先修复")
    references = {**mapping, **{old: 0 for old in removed}}
    expected_authors = []
    for old, new in mapping.items():
        row = list(by_id[old])
        row[id_index] = new
        expected_authors.append(tuple(row))
    expected_videos = []
    for original in videos:
        row = list(original)
        if row[author_index] is not None:
            row[author_index] = references[row[author_index]]
        expected_videos.append(tuple(row))
    return (removed, mapping, references, expected_authors, expected_videos,
            sum(old != new for old, new in mapping.items()),
            sum(a != b for a, b in zip(videos, expected_videos)))


def backup_database(path):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.backup-{timestamp}")
    # 独占创建，避免覆盖已有备份；使用备份接口包含 WAL 数据。
    with backup.open("xb"):
        pass
    source = destination = None
    try:
        source = connect(path, readonly=True)
        destination = sqlite3.connect(backup)
        source.backup(destination)
        result = list(destination.execute("PRAGMA integrity_check"))
        if result != [("ok",)]:
            raise RuntimeError(f"备份完整性检查失败: {result}")
    except Exception as exc:
        raise RuntimeError(f"备份失败（文件: {backup}）: {exc}") from exc
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
    print(f"备份路径: {backup}", flush=True)
    return backup


def clean(path, dry_run=False):
    conn = connect(path, readonly=dry_run)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
        (removed, mapping, references, expected_authors, expected_videos,
         changed_authors, changed_videos) = inspect(conn)
        print(f"{'预览' if dry_run else '计划'}: 删除 {len(removed)} 位作者，"
              f"重排 {changed_authors} 位作者，更新 {changed_videos} 条视频关联")
        print(f"剩余作者: {len(mapping)}，ID 范围: 0～{len(mapping) - 1}")
        if dry_run:
            conn.rollback()
            return
        # BEGIN IMMEDIATE 阻止其他写入者，独立读连接可备份修改前的状态。
        backup_database(path)
        conn.execute("PRAGMA defer_foreign_keys = ON")
        conn.execute("CREATE TEMP TABLE author_mapping "
                     "(old_id INTEGER PRIMARY KEY, new_id INTEGER NOT NULL)")
        conn.executemany("INSERT INTO author_mapping VALUES (?, ?)",
                         references.items())
        conn.execute("UPDATE videos SET author = "
                     "(SELECT new_id FROM author_mapping WHERE old_id = videos.author) "
                     "WHERE author IS NOT NULL AND author != "
                     "(SELECT new_id FROM author_mapping WHERE old_id = videos.author)")
        conn.executemany("DELETE FROM authors WHERE id = ?",
                         ((old,) for old in removed))
        # 全部先移至低于现有 ID 的临时值，再写入最终 ID，避免唯一约束冲突。
        lowest = min(0, min(references))
        temporary = [(old, lowest - index, new)
                     for index, (old, new) in enumerate(mapping.items(), 1)
                     if old != 0 and old != new]
        conn.executemany("UPDATE authors SET id = ? WHERE id = ?",
                         ((temp, old) for old, temp, new in temporary))
        conn.executemany("UPDATE authors SET id = ? WHERE id = ?",
                         ((new, temp) for old, temp, new in temporary))
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'authors'")
        conn.execute("INSERT INTO sqlite_sequence(name, seq) VALUES ('authors', ?)",
                     (max(mapping.values()),))
        if conn.execute("SELECT * FROM authors ORDER BY id").fetchall() != expected_authors:
            raise RuntimeError("作者数据或编号验证失败")
        if conn.execute("SELECT * FROM videos ORDER BY id").fetchall() != expected_videos:
            raise RuntimeError("视频数据或关联验证失败")
        if list(conn.execute("PRAGMA foreign_key_check")):
            raise RuntimeError("修改后的外键检查失败")
        if list(conn.execute("PRAGMA integrity_check")) != [("ok",)]:
            raise RuntimeError("修改后的数据库完整性检查失败")
        conn.commit()
        print("清理完成，验证通过。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="数据库路径")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不修改或备份")
    args = parser.parse_args()
    try:
        clean(args.db.resolve(), args.dry_run)
    except (sqlite3.Error, OSError, RuntimeError, ValueError) as exc:
        print(f"失败，数据库修改已回滚: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
