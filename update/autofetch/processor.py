#!/usr/bin/env python3
"""
从 CSV 中读取 B 站视频链接，通过 yt-dlp 获取视频简介，
按配置规则提取原视频链接并格式化，再反查原作者频道名。

配置文件：config/processor.jsonc
CSV 目录：output/

命令行可用 --time-range 覆盖配置中的时间范围。

新增：支持通过配置文件指定 cookies 文件，yt-dlp 携带 cookies 访问 B 站。
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from env import load_dotenv

parse_time_range = import_module("time-range").parse_time_range

# ==================== JSONC 解析 ====================


def load_jsonc(filepath: str) -> dict:
    """加载 JSONC 配置文件（支持 // 和 /* */ 注释）。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 移除多行注释
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # 逐行移除单行注释（状态机保护字符串）
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        in_double = False
        in_single = False
        comment_idx = -1
        i = 0
        while i < len(line) - 1:
            c = line[i]
            if in_double:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_double = False
            elif in_single:
                if c == "\\":
                    i += 2
                    continue
                if c == "'":
                    in_single = False
            else:
                if c == '"':
                    in_double = True
                elif c == "'":
                    in_single = True
                elif c == "/" and line[i + 1] == "/":
                    comment_idx = i
                    break
            i += 1
        if comment_idx >= 0:
            line = line[:comment_idx]
        cleaned.append(line)

    return json.loads("\n".join(cleaned))


# ==================== Cookies 配置 ====================


def resolve_cookies(config: dict, script_dir: Path) -> Optional[str]:
    """
    解析 cookies 配置，返回 cookies 文件的绝对路径，或 None（不启用）。
    """
    cookies_cfg = config.get("cookies", {})
    if not cookies_cfg.get("enabled", False):
        return None

    file_rel = cookies_cfg.get("file", "cookies.txt")
    file_path = Path(file_rel)
    if not file_path.is_absolute():
        file_path = script_dir / file_rel

    if not file_path.exists():
        print(f"[警告] cookies 文件不存在: {file_path}")
        return None

    return str(file_path)


# ==================== 时间范围解析 ====================

TZ_BEIJING = timezone(timedelta(hours=8))

DATE_PATTERN = re.compile(r"(\d{8})")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="处理 autofetch CSV")
    parser.add_argument(
        "--time-range",
        type=parse_time_range,
        help="覆盖配置中的时间范围：today、yesterday、all、YYYYMMDD 或最近 N 个自然日",
    )
    parser.add_argument("--csv-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--resume", action="store_true", help="只继续未完成视频；需配合 --report"
    )
    return parser.parse_args(argv)


def resolve_time_range(process_config: dict) -> str:
    """
    解析最终时间范围值。
    优先使用 process_config["time_range"]，
    若为 None 则从 fetch_config_path 指向的配置文件回退读取。
    """
    tr = process_config.get("time_range")
    if tr is not None:
        return tr

    script_dir = Path(__file__).resolve().parent
    fetch_rel = process_config.get("fetch_config_path", "config/fetcher.jsonc")
    fetch_path = script_dir / fetch_rel

    if fetch_path.exists():
        fetch_cfg = load_jsonc(str(fetch_path))
        return fetch_cfg.get("time_range", "today")

    return "today"


def csv_matches_time_range(csv_path: Path, time_range: Any) -> bool:
    """判断 CSV 文件名中的日期是否匹配时间范围。"""
    m = DATE_PATTERN.search(csv_path.stem)
    if not m:
        return False

    file_date_str = m.group(1)
    try:
        file_date = datetime.strptime(file_date_str, "%Y%m%d").date()
    except ValueError:
        return False

    if time_range == "all":
        return True
    if time_range == "today":
        return file_date == datetime.now(TZ_BEIJING).date()
    if time_range == "yesterday":
        return file_date == datetime.now(TZ_BEIJING).date() - timedelta(days=1)
    if isinstance(time_range, (int, float)):
        days = int(time_range)
        today = datetime.now(TZ_BEIJING).date()
        return (today - file_date).days < days
    if isinstance(time_range, str) and re.match(r"^\d{8}$", time_range):
        return file_date_str == time_range

    return False


# ==================== yt-dlp 调用封装 ====================


def check_ytdlp() -> bool:
    """检查 yt-dlp 是否可用。"""
    try:
        subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ytdlp_get_field(
    url: str,
    field: str,
    cookies_file: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """
    通过 yt-dlp 获取视频元数据字段。
    若提供 cookies_file，则携带 cookies 请求。
    """
    cmd = [
        "yt-dlp",
        "--print",
        field,
        "--no-download",
        "--no-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--quiet",
    ]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        # 调试：输出 stderr 以便排查
        if result.stderr.strip():
            # 只打印前两行，避免刷屏
            stderr_lines = result.stderr.strip().split("\n")[:2]
            for line in stderr_lines:
                print(f"    [yt-dlp] {line}")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"    [yt-dlp 异常] {e}")
    return ""


def get_description(
    url: str,
    cookies_file: Optional[str] = None,
    timeout: int = 60,
) -> Optional[str]:
    """通过 yt-dlp 获取视频简介（纯文本）。"""
    return ytdlp_get_field(url, "description", cookies_file, timeout) or None


def get_author_from_original_link(
    original_url: str,
    config: dict,
    cookies_file: Optional[str] = None,
    description: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """
    从原视频链接获取作者频道名。

    策略：
    1. 如果启用 yt-dlp，依次尝试配置的字段
    2. 若失败，使用配置的 fallback_patterns 从简介中提取
    """
    author_cfg = config.get("author_extraction", {})

    # 策略 1：yt-dlp
    if author_cfg.get("use_ytdlp", True):
        fields = author_cfg.get(
            "ytdlp_fields",
            ["channel", "uploader", "creator", "channel_id"],
        )
        for field in fields:
            name = ytdlp_get_field(original_url, field, cookies_file, timeout)
            if name:
                return name.strip()

    # 策略 2：从简介中正则提取
    if description:
        fallback_patterns = author_cfg.get("fallback_patterns", [])
        for fb in fallback_patterns:
            pattern = fb.get("pattern", "")
            group = fb.get("group", 1)
            m = re.search(pattern, description, re.MULTILINE)
            if m:
                name = m.group(group).strip()
                name = re.sub(r"\s*(?:https?://.*|$)", "", name).strip()
                if name:
                    return name

    return ""


# ==================== 原视频链接提取 ====================


def extract_original_link(description: str, rules: list) -> Optional[str]:
    """按规则列表顺序匹配，返回第一个命中的 URL。"""
    for rule in rules:
        pattern = rule.get("pattern", "")
        group = rule.get("group", 1)
        m = re.search(pattern, description, re.MULTILINE)
        if m:
            url = m.group(group).strip()
            url = re.sub(r'[。，,;；:："\'」】)）>}\]>"]+$', "", url)
            if url:
                rule_name = rule.get("name", rule.get("comment", "未命名规则"))
                print(f"    命中规则: {rule_name}")
                return url
    return None


# ==================== 链接格式化 ====================


def format_link(raw_url: str, format_config: dict) -> str:
    """
    按配置格式化原视频链接：
    - 移除 tracking 参数
    - youtu.be → youtube.com/watch?v=
    - m.youtube.com → www.youtube.com
    - 清理尾部标点
    """
    url = raw_url.strip()

    if format_config.get("clean_trailing", True):
        url = re.sub(r'[。，,;；:："\'」】)）>}\]>"]+$', "", url)

    nico_id_match = re.match(r"^(sm|nm|so)\d+$", url, re.IGNORECASE)
    if nico_id_match:
        url = f"https://www.nicovideo.jp/watch/{url}"
        return url

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url

    netloc = parsed.netloc.lower()

    # youtu.be → www.youtube.com/watch?v=
    if format_config.get("normalize_youtube", True):
        if netloc == "youtu.be":
            path = parsed.path.lstrip("/")
            return f"https://www.youtube.com/watch?v={path}"

    # m.youtube.com → www.youtube.com
    if format_config.get("normalize_mobile", True):
        netloc = re.sub(r"^m\.", "www.", netloc)

    # 移除查询参数
    remove_params = format_config.get("remove_params", [])
    if remove_params:
        params = parse_qs(parsed.query, keep_blank_values=False)
        for key in list(params.keys()):
            if key in remove_params:
                del params[key]
        new_query = urlencode(params, doseq=True)
    else:
        new_query = parsed.query

    new_parsed = parsed._replace(netloc=netloc, query=new_query, fragment="")
    result = urlunparse(new_parsed)

    if format_config.get("clean_trailing", True):
        result = re.sub(r'[。，,;；:："\'」】)）>}\]>"]+$', "", result)

    return result


# ==================== CSV 处理 ====================


def read_csv_rows(filepath: Path) -> list[list[str]]:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def write_csv_rows(filepath: Path, rows: list[list[str]]):
    temporary = filepath.with_suffix(filepath.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
        csv.writer(stream).writerows(rows)
    os.replace(temporary, filepath)


def ensure_columns(row: list, min_cols: int = 5) -> list:
    while len(row) < min_cols:
        row.append("")
    return row


# ==================== 主流程 ====================


def main(argv=None):
    args = parse_args(argv)
    if args.resume and not args.report:
        raise ValueError("--resume 需要 --report")
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / "config" / ".env", quiet=True)
    config_path = script_dir / "config" / "processor.jsonc"

    if not config_path.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        sys.exit(1)

    # ---------- 加载配置 ----------
    process_config = load_jsonc(str(config_path))

    # 解析 cookies
    cookies_file = resolve_cookies(process_config, script_dir)
    if cookies_file:
        print(f"→ Cookies: {cookies_file}")
    else:
        print("→ Cookies: 未启用（B 站简介可能获取失败）")

    time_range = (
        args.time_range
        if args.time_range is not None
        else resolve_time_range(process_config)
    )

    csv_dir = args.csv_dir or Path(process_config.get("csv_dir", "output"))
    if not csv_dir.is_absolute():
        csv_dir = script_dir / csv_dir

    extraction_rules = process_config.get("extraction_rules", [])
    if not extraction_rules:
        print("[错误] 未配置 extraction_rules")
        sys.exit(1)

    link_format_cfg = process_config.get("link_format", {})
    skip_existing = process_config.get("skip_existing", True)
    request_delay = process_config.get("request_delay", 1.0)

    # ---------- 检查 yt-dlp ----------
    if not check_ytdlp():
        print("[错误] yt-dlp 未安装或不可用。请运行: pip install yt-dlp")
        sys.exit(1)

    # ---------- 查找匹配的 CSV ----------
    print(f"→ 时间范围: {time_range}")
    print(f"→ CSV 目录: {csv_dir}")

    if not csv_dir.exists():
        print(f"[错误] CSV 目录不存在: {csv_dir}")
        sys.exit(1)

    csv_files = sorted(csv_dir.glob("*.csv"))
    matched_csv = [f for f in csv_files if csv_matches_time_range(f, time_range)]

    if not matched_csv:
        print("[警告] 没有找到匹配时间范围的 CSV 文件")
        if args.report:
            from fetcher import save_state

            save_state(args.report, {"complete": True, "failures": []})
        return

    print(f"→ 匹配到 {len(matched_csv)} 个 CSV 文件:\n")
    for f in matched_csv:
        print(f"   {f.name}")

    from fetcher import save_state

    previous = (
        json.loads(args.report.read_text())
        if args.resume and args.report.exists()
        else {}
    )
    saved = previous.get("videos", {})
    records = {}
    file_failures = []
    inputs = []
    for csv_path in matched_csv:
        try:
            rows = read_csv_rows(csv_path)
        except Exception:
            file_failures.append(
                {"stage": "csv", "file": csv_path.name, "retryable": True}
            )
            continue
        for index, raw in enumerate(rows):
            row = ensure_columns(raw, 5)
            if not row[3].strip():
                continue
            key = f"{csv_path.name}:{index + 1}"
            prior = saved.get(key, {})
            if prior.get("fingerprint") == row:
                records[key] = prior
            else:
                records[key] = {"status": "pending", "fingerprint": row.copy()}
            inputs.append((csv_path, rows, index, key))

    def problems():
        result = list(file_failures)
        for key, record in records.items():
            if record["status"] != "complete":
                result.append(
                    record.get(
                        "failure",
                        {
                            "stage": "pending",
                            "file": key.split(":")[0],
                            "video": record["fingerprint"][3],
                            "title": record["fingerprint"][2],
                            "retryable": True,
                        },
                    )
                )
        return result

    def progress():
        if args.report:
            issues = problems()
            save_state(
                args.report,
                {
                    "version": 2,
                    "complete": not issues,
                    "failures": issues,
                    "videos": records,
                    "completed_videos": sum(
                        r["status"] == "complete" for r in records.values()
                    ),
                    "total_videos": len(records),
                },
            )

    progress()
    processed = skipped = 0
    for csv_path, rows, index, key in inputs:
        row = rows[index]
        record = records[key]
        if args.resume and record["status"] in ("complete", "manual"):
            skipped += 1
            continue
        video = row[3].strip()
        issue = None
        changed = False
        # Existing manually entered original links are never replaced to retry an author.
        existing_complete = row[1].strip() and (not args.report or row[0].strip())
        if skip_existing and existing_complete:
            skipped += 1
        else:
            print(f"→ {csv_path.name}:{index+1} {row[2][:100]} ({video})")
            try:
                description = None
                if not row[1].strip() or not skip_existing:
                    description = get_description(video, cookies_file)
                    if not description:
                        issue = ("description", True)
                    else:
                        original = extract_original_link(description, extraction_rules)
                        if not original:
                            issue = ("original_link_missing", False)
                        else:
                            row[1] = format_link(original, link_format_cfg)
                            changed = True
                if not issue:
                    author = get_author_from_original_link(
                        row[1],
                        process_config,
                        cookies_file=cookies_file,
                        description=description,
                    )
                    if author:
                        row[0] = author
                        changed = True
                    else:
                        issue = ("author", True)
            except Exception:
                issue = ("metadata_request", True)
            time.sleep(request_delay)
        try:
            if changed:
                rows[index] = row
                write_csv_rows(csv_path, rows)
                processed += 1
        except OSError:
            issue = ("csv", True)
        record["fingerprint"] = row.copy()
        if issue:
            stage, retryable = issue
            record["status"] = "pending" if retryable else "manual"
            record["failure"] = {
                "stage": stage,
                "retryable": retryable,
                "file": csv_path.name,
                "csv_path": str(csv_path),
                "row": index + 1,
                "video": video,
                "title": row[2],
                "author": row[0] or csv_path.stem.rsplit("-", 1)[0],
            }
            print(f"  {'稍后重试' if retryable else '需要人工补充原链接'}：{video}")
        else:
            record["status"] = "complete"
            record.pop("failure", None)
        progress()
    issues = problems()
    print(
        f"本轮结束：写入 {processed} 条，跳过 {skipped} 条，未完成 {len(issues)} 项。"
    )
    if args.report and issues:
        sys.exit(2 if any(f.get("retryable", True) for f in issues) else 3)


if __name__ == "__main__":
    main()
