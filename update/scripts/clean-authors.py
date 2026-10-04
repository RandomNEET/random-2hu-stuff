#!/usr/bin/env python3
"""清理新作者；已部署空作者须逐项确认后用末尾作者填补，修改前自动备份。"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "backend/random-2hu-stuff.db"
DEFAULT_LOG = Path(__file__).resolve().with_name("content.log")


def read_deployed_boundary(log_path):
    """Use the last nonempty log row's author count as the requested ID boundary."""
    lines = [
        line.strip()
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError(f"部署日志为空: {log_path}")
    fields = lines[-1].split(",")
    if len(fields) != 3 or any(not field.strip().isdigit() for field in fields):
        raise ValueError(f"部署日志最后一行格式无效: {lines[-1]!r}")
    return int(fields[0])


def connect(path, readonly=False):
    mode = "ro" if readonly else "rw"
    return sqlite3.connect(
        f"{path.resolve().as_uri()}?mode={mode}",
        uri=True,
        timeout=30,
        isolation_level=None,
    )


def inspect(conn, deployed_boundary, replacements=()):
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
        row[id_index]
        for row in authors
        if row[id_index] > deployed_boundary
        and all(value is None for i, value in enumerate(row) if i != id_index)
    }
    donors = {donor for target, donor in replacements}
    for target, donor in replacements:
        if (
            target == 0
            or target > deployed_boundary
            or target not in by_id
            or any(
                value is not None
                for i, value in enumerate(by_id[target])
                if i != id_index
            )
            or donor not in by_id
            or donor <= target
            or donor in removed
        ):
            raise RuntimeError("替换计划已失效，请重新运行")
        removed.add(target)
    mapping = {
        old: old
        for old in sorted(by_id)
        if old <= deployed_boundary and old not in removed and old not in donors
    }
    mapping.update({donor: target for target, donor in replacements})
    mapping.update(
        {
            old: new
            for new, old in enumerate(
                (
                    old
                    for old in sorted(by_id)
                    if old > deployed_boundary
                    and old not in removed
                    and old not in donors
                ),
                deployed_boundary + 1,
            )
        }
    )
    videos = conn.execute("SELECT * FROM videos ORDER BY id").fetchall()
    video_columns = [row[1] for row in conn.execute("PRAGMA table_info(videos)")]
    author_index = video_columns.index("author")
    if any(
        row[author_index] is not None and row[author_index] not in by_id
        for row in videos
    ):
        raise RuntimeError("videos 中存在失效作者关联，请先修复")
    references = {**mapping, **{old: 0 for old in removed}}
    expected_authors = []
    for old, new in sorted(mapping.items(), key=lambda item: item[1]):
        row = list(by_id[old])
        row[id_index] = new
        expected_authors.append(tuple(row))
    expected_videos = []
    for original in videos:
        row = list(original)
        if row[author_index] is not None:
            row[author_index] = references[row[author_index]]
        expected_videos.append(tuple(row))
    return (
        removed,
        mapping,
        references,
        expected_authors,
        expected_videos,
        sum(old != new for old, new in mapping.items()),
        sum(a != b for a, b in zip(videos, expected_videos)),
    )


def choose_replacements(conn, deployed_boundary, dry_run=False):
    """Prompt before taking a write lock; choose the current last nonempty author."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(authors)")]
    id_index = columns.index("id")
    authors = {
        row[id_index]: row for row in conn.execute("SELECT * FROM authors ORDER BY id")
    }
    empty = {
        old
        for old, row in authors.items()
        if all(value is None for i, value in enumerate(row) if i != id_index)
    }
    active = set(authors) - empty - {0}
    counts = dict(conn.execute("SELECT author, COUNT(*) FROM videos GROUP BY author"))
    replacements = []
    no_input = False
    for target in sorted(empty):
        if target == 0 or target > deployed_boundary:
            continue
        eligible = [old for old in active if old > target]
        if not eligible:
            print(f"已部署空作者 id={target}：没有可替换的末尾作者，保留。")
            continue
        donor = max(eligible)
        print(f"\n待确认：末尾作者 id={donor} → 已部署空作者 id={target}")
        for column, value in zip(columns, authors[donor]):
            print(f"  {column}: {value!r}")
        print(f"  末尾作者的 {counts.get(donor, 0)} 条视频将改为 author={target}。")
        print(f"  空作者原有的 {counts.get(target, 0)} 条视频将转给作者 0。")
        if dry_run:
            print("  预览：尚未确认，不替换。")
            continue
        answer = ""
        while not no_input:
            try:
                answer = input("确认此替换？[y/N]（仅 y/yes 确认）: ").strip().lower()
            except EOFError:
                no_input = True
                print("无输入，跳过所有未确认替换。")
                break
            if answer in ("", "n", "no", "y", "yes"):
                break
            print("请输入 y/yes 确认，n/no 或直接回车跳过。")
        if answer in ("y", "yes"):
            replacements.append((target, donor))
            active.remove(donor)
            print("  已确认，将在备份成功后执行。")
        else:
            print(f"  已跳过，id={target} 保持不变。")
    return replacements


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


def clean(path, dry_run=False, log_path=DEFAULT_LOG):
    deployed_boundary = read_deployed_boundary(log_path)
    conn = connect(path, readonly=dry_run)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        # Validate before prompting. No database lock is held while waiting for input.
        inspect(conn, deployed_boundary)
        original_authors = conn.execute("SELECT * FROM authors ORDER BY id").fetchall()
        original_videos = conn.execute("SELECT * FROM videos ORDER BY id").fetchall()
        replacements = choose_replacements(conn, deployed_boundary, dry_run)
        conn.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
        if (
            conn.execute("SELECT * FROM authors ORDER BY id").fetchall()
            != original_authors
            or conn.execute("SELECT * FROM videos ORDER BY id").fetchall()
            != original_videos
            or read_deployed_boundary(log_path) != deployed_boundary
        ):
            raise RuntimeError("确认期间数据库或部署边界发生变化，请重新预览并确认")
        (
            removed,
            mapping,
            references,
            expected_authors,
            expected_videos,
            changed_authors,
            changed_videos,
        ) = inspect(conn, deployed_boundary, replacements)
        print(
            f"部署日志: {log_path}；保护 ID ≤ {deployed_boundary}（仅逐项确认的空作者允许替换）"
        )
        print(
            f"{'预览' if dry_run else '计划'}: 删除 {len(removed)} 位作者，"
            f"重排 {changed_authors} 位作者，更新 {changed_videos} 条视频关联"
        )
        print(
            f"剩余作者: {len(mapping)}，ID 范围: {min(mapping.values())}～{max(mapping.values())}"
        )
        print("待删除作者完整清单（除 id 外所有字段均为 NULL）:")
        for old in sorted(removed):
            count = conn.execute(
                "SELECT COUNT(*) FROM videos WHERE author = ?", (old,)
            ).fetchone()[0]
            print(f"  id={old}，关联视频 {count} 条（转给作者 0）")
        for target, donor in replacements:
            print(
                f"已确认替换: 原作者 id={donor} → 空位 id={target}；原末尾 ID 不再保留。"
            )
        if not removed:
            print("  无")
        columns = [
            row[1]
            for row in conn.execute("PRAGMA table_info(authors)")
            if row[1] != "id"
        ]
        null_condition = " AND ".join(
            '"' + column.replace('"', '""') + '" IS NULL' for column in columns
        )
        protected_empty = conn.execute(
            f"SELECT id FROM authors WHERE id > 0 AND id <= ? AND {null_condition} ORDER BY id",
            (deployed_boundary,),
        ).fetchall()
        preserved_empty = [row[0] for row in protected_empty if row[0] not in removed]
        if preserved_empty:
            print(
                "已部署的全 NULL 作者，保留不动: "
                + ", ".join(map(str, preserved_empty))
            )
        if dry_run:
            conn.rollback()
            return
        # BEGIN IMMEDIATE 阻止其他写入者，独立读连接可备份修改前的状态。
        backup_database(path)
        conn.execute("PRAGMA defer_foreign_keys = ON")
        conn.execute(
            "CREATE TEMP TABLE author_mapping "
            "(old_id INTEGER PRIMARY KEY, new_id INTEGER NOT NULL)"
        )
        conn.executemany("INSERT INTO author_mapping VALUES (?, ?)", references.items())
        conn.execute(
            "UPDATE videos SET author = "
            "(SELECT new_id FROM author_mapping WHERE old_id = videos.author) "
            "WHERE author IS NOT NULL AND author != "
            "(SELECT new_id FROM author_mapping WHERE old_id = videos.author)"
        )
        conn.executemany(
            "DELETE FROM authors WHERE id = ?", ((old,) for old in removed)
        )
        # 全部先移至低于现有 ID 的临时值，再写入最终 ID，避免唯一约束冲突。
        lowest = min(0, min(references))
        temporary = [
            (old, lowest - index, new)
            for index, (old, new) in enumerate(mapping.items(), 1)
            if old != 0 and old != new
        ]
        conn.executemany(
            "UPDATE authors SET id = ? WHERE id = ?",
            ((temp, old) for old, temp, new in temporary),
        )
        conn.executemany(
            "UPDATE authors SET id = ? WHERE id = ?",
            ((new, temp) for old, temp, new in temporary),
        )
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'authors'")
        conn.execute(
            "INSERT INTO sqlite_sequence(name, seq) VALUES ('authors', ?)",
            (max(deployed_boundary, max(mapping.values())),),
        )
        if (
            conn.execute("SELECT * FROM authors ORDER BY id").fetchall()
            != expected_authors
        ):
            raise RuntimeError("作者数据或编号验证失败")
        if (
            conn.execute("SELECT * FROM videos ORDER BY id").fetchall()
            != expected_videos
        ):
            raise RuntimeError("视频数据或关联验证失败")
        if list(conn.execute("PRAGMA foreign_key_check")):
            raise RuntimeError("修改后的外键检查失败")
        if list(conn.execute("PRAGMA integrity_check")) != [("ok",)]:
            raise RuntimeError("修改后的数据库完整性检查失败")
        conn.commit()
        print("清理完成，验证通过。")
        print("实际已删除作者 ID: " + (", ".join(map(str, sorted(removed))) or "无"))
        for target, donor in replacements:
            print(
                f"实际已替换: 作者原 ID {donor} → {target}（空记录被替换，ID {target} 保留）"
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="数据库路径")
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG,
        help="部署日志路径（默认脚本同目录 content.log）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只预览，不修改或备份")
    args = parser.parse_args()
    try:
        clean(args.db.resolve(), args.dry_run, args.log.resolve())
    except KeyboardInterrupt:
        print("已取消，数据库未提交修改。", file=sys.stderr)
        return 130
    except (sqlite3.Error, OSError, RuntimeError, ValueError) as exc:
        print(f"失败，数据库修改已回滚: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
