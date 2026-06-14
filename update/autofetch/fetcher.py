#!/usr/bin/env python3
"""
从 RSSHub 获取 B 站用户视频信息，筛选时间范围内的视频并输出 CSV。

配置文件：config/fetcher.jsonc
CSV 输出：output/author-YYYYMMDD.csv
CSV 格式：空, 空, title, link, 翻译状态
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

# ==================== JSONC 解析 ====================


def load_jsonc(filepath: str) -> dict:
    """
    加载 JSONC 配置文件（支持 // 和 /* */ 注释）。
    使用状态机识别字符串边界，避免误删字符串内的 //。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 移除多行注释 /* ... */
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # 2. 逐行处理单行注释 //
    lines = content.split("\n")
    cleaned_lines = []
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
        cleaned_lines.append(line)

    return json.loads("\n".join(cleaned_lines))


# ==================== 用户配置归一化 ====================


def normalize_user_config(raw_entry, defaults: dict) -> dict:
    """
    将 users 列表中的每一个条目统一为内部格式：
    {
        "id": str,
        "translation_status": int | "auto",
        "keyword_map": dict[str, int],
        "fallback": int | None
    }
    """
    if isinstance(raw_entry, str):
        entry = {"id": raw_entry}
    elif isinstance(raw_entry, dict):
        entry = raw_entry.copy()
    else:
        raise TypeError(f"users 条目必须是字符串或对象，得到: {type(raw_entry)}")

    uid = str(entry.get("id", "")).strip()
    if not uid:
        raise ValueError(f"用户条目缺少 id: {entry}")

    return {
        "id": uid,
        "translation_status": entry.get(
            "translation_status", defaults["translation_status"]
        ),
        "keyword_map": entry.get("keyword_map", defaults["keyword_map"]),
        "fallback": entry.get("fallback", defaults["fallback"]),
    }


# ==================== 日期工具 ====================

TZ_BEIJING = timezone(timedelta(hours=8))


def parse_pub_date(date_str: str) -> datetime | None:
    """解析 RSS pubDate（RFC 2822 格式），返回 UTC datetime。"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%a, %d %b %Y %H:%M:%S %Z")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_within_range(dt: datetime | None, time_range: Any) -> bool:
    """
    判断视频发布时间是否在时间范围内。
    - "today": 仅当天（北京时间）
    - "all":   所有视频
    - int:     最近 N 天（含今天）
    """
    if dt is None:
        return False
    if time_range == "all":
        return True

    now = datetime.now(TZ_BEIJING)
    dt_beijing = dt.astimezone(TZ_BEIJING)

    if time_range == "today":
        return dt_beijing.date() == now.date()

    if isinstance(time_range, (int, float)):
        days = int(time_range)
        delta = now - dt_beijing
        return delta.days < days

    return False


# ==================== 翻译状态判断（auto 模式） ====================


def determine_translation_status(title: str, user_cfg: dict) -> int | str:
    """
    根据用户配置决定 CSV 第五列的值。

    返回:
        int  - 翻译状态 1~5
        ""   - 留空（fallback 为 null 且无匹配时）
    """
    ts = user_cfg["translation_status"]

    # 数字模式：固定值
    if isinstance(ts, int):
        return ts

    # auto 模式：关键字匹配
    if ts == "auto":
        keyword_map = user_cfg.get("keyword_map", {})
        # 按配置中的顺序依次匹配（Python 3.7+ dict 保序）
        for keyword, status in keyword_map.items():
            if keyword and keyword in title:
                return int(status)

        # 无匹配 → 回退
        fallback = user_cfg.get("fallback")
        if fallback is None:
            return ""  # CSV 留空
        return int(fallback)

    # 兜底
    return ""


# ==================== RSS 获取与解析 ====================


def fetch_rss(baseurl: str, user_id: str) -> str:
    """从 RSSHub 获取指定用户的视频 RSS XML。"""
    url = f"{baseurl.rstrip('/')}/bilibili/user/video/{user_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_rss(xml_content: str) -> tuple[str | None, list[dict]]:
    """
    解析 RSS XML。
    返回: (作者名, [{"title":..., "link":..., "pubDate":...}, ...])
    """
    root = ET.fromstring(xml_content)
    channel = root.find("channel")
    if channel is None:
        return None, []

    # 提取作者名（去掉 " 的 bilibili 空间" 后缀）
    title_elem = channel.find("title")
    author = "unknown"
    if title_elem is not None and title_elem.text:
        author = title_elem.text.strip()
        author = re.sub(r"\s*的\s*bilibili\s*空间\s*$", "", author).strip()

    items = []
    for item in channel.findall("item"):
        t = item.find("title")
        l = item.find("link")
        p = item.find("pubDate")
        items.append(
            {
                "title": t.text if t is not None and t.text else "",
                "link": l.text if l is not None and l.text else "",
                "pubDate": p.text if p is not None and p.text else "",
            }
        )

    return author, items


# ==================== 主流程 ====================


def main():
    script_dir = Path(__file__).resolve().parent

    # 配置文件位于 config/ 子目录
    config_path = script_dir / "config" / "fetcher.jsonc"
    if not config_path.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        sys.exit(1)

    config = load_jsonc(str(config_path))

    # ---------- 全局默认值 ----------
    baseurl = config.get("baseurl", "https://rsshub.defnothowl.com")
    time_range = config.get("time_range", "today")
    defaults = {
        "translation_status": config.get("default_translation_status", "auto"),
        "keyword_map": config.get("default_keyword_map", {}),
        "fallback": config.get("default_fallback", 5),
    }

    # ---------- 归一化用户列表 ----------
    raw_users = config.get("users", [])
    if not raw_users:
        print("[错误] 配置文件中 users 为空，请至少指定一个用户")
        sys.exit(1)

    users = []
    for entry in raw_users:
        try:
            users.append(normalize_user_config(entry, defaults))
        except (ValueError, TypeError) as e:
            print(f"[警告] 跳过无效用户条目: {e}")

    if not users:
        print("[错误] 没有有效的用户配置")
        sys.exit(1)

    # ---------- 收集视频数据 ----------
    grouped_rows = defaultdict(list)
    total_matched = 0

    for user_cfg in users:
        uid = user_cfg["id"]
        print(f"→ 正在获取用户 {uid} 的视频 RSS ...")
        try:
            xml_content = fetch_rss(baseurl, uid)
            author, items = parse_rss(xml_content)
            print(f"  作者: {author}  |  RSS 共返回 {len(items)} 条")

            matched = 0
            for item in items:
                pub_dt = parse_pub_date(item["pubDate"])
                if not is_within_range(pub_dt, time_range):
                    continue

                ts = determine_translation_status(item["title"], user_cfg)
                grouped_rows[author].append(
                    {
                        "title": item["title"],
                        "link": item["link"],
                        "translation_status": ts,
                    }
                )
                matched += 1
                total_matched += 1

            print(f"  命中时间范围: {matched} 条")

        except requests.RequestException as e:
            print(f"  [警告] 网络请求失败: {e}")
            continue
        except ET.ParseError as e:
            print(f"  [警告] XML 解析失败: {e}")
            continue
        except Exception as e:
            print(f"  [警告] 未知错误: {e}")
            continue

    if total_matched == 0:
        print("\n没有找到符合时间范围的视频，未生成 CSV。")
        return

    # ---------- 按作者输出 CSV 到 output/ 目录 ----------
    output_dir = script_dir / "output"
    os.makedirs(output_dir, exist_ok=True)

    today_str = datetime.now(TZ_BEIJING).strftime("%Y%m%d")

    for author, rows in grouped_rows.items():
        safe_author = re.sub(r'[\\/:*?"<>|]', "_", author)
        filename = f"{safe_author}-{today_str}.csv"
        filepath = output_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            for row in rows:
                # 第 1、2 列留空 | 第 3 列 title | 第 4 列 link | 第 5 列 翻译状态
                writer.writerow(
                    ["", "", row["title"], row["link"], row["translation_status"]]
                )

        print(f"\n✓ 已生成: {filepath}  ({len(rows)} 条记录)")

    print(f"\n完成！共处理 {len(users)} 个用户，输出 {total_matched} 条视频。")


if __name__ == "__main__":
    main()
