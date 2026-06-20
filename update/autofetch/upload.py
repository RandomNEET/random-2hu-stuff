#!/usr/bin/env python3
"""
腾讯文档上传 + 整理一体脚本
用法：
    python upload.py                  # 全流程：合并本地 CSV → 上传 → 整理在线表格
    python upload.py --check-only     # 仅本地处理（不实际上传）
    python upload.py --upload-only    # 仅上传已有的 combined 文件 → 然后整理
    python upload.py --order-only     # 仅整理在线表格（不处理本地文件）
    python upload.py --dry-run        # 试运行（所有写操作均为预览）
    python upload.py --order-only --file-id <ID> --sheet-id <ID>  # 手动指定表格
"""

import copy
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List

import json5
import requests


# ==================== 1. 加载 .env ====================
def load_dotenv(dotenv_path: Path = Path("config/.env")):
    if not dotenv_path.exists():
        print(f"[提示] 未找到 {dotenv_path}，将使用已存在的环境变量")
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value


load_dotenv()

ACCESS_TOKEN = os.getenv("TENCENT_DOCS_ACCESS_TOKEN")
CLIENT_ID = os.getenv("TENCENT_DOCS_CLIENT_ID")
OPEN_ID = os.getenv("TENCENT_DOCS_OPEN_ID")


# ==================== 2. 配置加载 ====================
def load_upload_config() -> dict:
    config_file = Path("config/upload.jsonc")
    if not config_file.exists():
        print(f"[提示] 配置文件 {config_file} 不存在，将尝试 fallback")
        return {}
    with open(config_file, "r", encoding="utf-8") as f:
        raw = f.read()
    cfg: Any = json5.loads(raw)
    if not isinstance(cfg, dict):
        raise TypeError(f"配置文件顶层应为对象/字典，实际为 {type(cfg).__name__}")
    return cfg


def load_fetcher_config() -> dict:
    config_file = Path("config/fetcher.jsonc")
    if not config_file.exists():
        return {}
    with open(config_file, "r", encoding="utf-8") as f:
        raw = f.read()
    cfg: Any = json5.loads(raw)
    if not isinstance(cfg, dict):
        raise TypeError(
            f"fetcher 配置文件顶层应为对象/字典，实际为 {type(cfg).__name__}"
        )
    return cfg


def get_time_range(cfg_upload: dict) -> str:
    tr = cfg_upload.get("time_range")
    if tr is not None:
        return tr
    fetcher_cfg = load_fetcher_config()
    return fetcher_cfg.get("time_range", "today")


# ==================== 3. 参数解析 ====================
def parse_args():
    check_only = False
    upload_only = False
    order_only = False
    dry_run = False
    file_id = None
    sheet_id = None
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--check-only", "--local-only"):
            check_only = True
        elif arg == "--upload-only":
            upload_only = True
        elif arg == "--order-only":
            order_only = True
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--file-id" and i + 1 < len(sys.argv):
            file_id = sys.argv[i + 1]
            i += 1
        elif arg == "--sheet-id" and i + 1 < len(sys.argv):
            sheet_id = sys.argv[i + 1]
            i += 1
        i += 1
    return check_only, upload_only, order_only, dry_run, file_id, sheet_id


# ==================== 4. 时间范围处理 ====================
def get_target_dates(time_range_str: str):
    if time_range_str in (None, "today"):
        return [datetime.now().strftime("%Y%m%d")]
    if time_range_str == "all":
        return []
    if str(time_range_str).isdigit():
        days = int(time_range_str)
        return [
            (datetime.now() - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)
        ]
    if re.match(r"^\d{8}$", str(time_range_str)):
        return [time_range_str]
    print(f"[警告] 无法识别的 time_range '{time_range_str}'，回退到今天")
    return [datetime.now().strftime("%Y%m%d")]


# ==================== 5. CSV 读取 ====================
def is_all_empty(row):
    return all(cell.strip() == "" for cell in row)


def dedup_cell(cell: str) -> str:
    parts = cell.strip().split()
    seen = set()
    unique = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return " ".join(unique)


def read_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or is_all_empty(row):
                continue
            cleaned = []
            for i, cell in enumerate(row):
                cell = cell.strip()
                if i in (1, 3) and cell:
                    cell = dedup_cell(cell)
                cleaned.append(cell)
            rows.append(cleaned)
    return rows


def trim_empty_first_column(rows):
    if not rows:
        return rows
    if all(len(r) > 0 and r[0].strip() == "" for r in rows):
        print("  [清洗] 检测到空第一列，已自动移除")
        return [r[1:] for r in rows]
    return rows


def deduplicate(rows):
    seen = set()
    unique = []
    for r in rows:
        key = tuple(r)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ==================== 6. 分组、整理与冲突检查 ====================
def process_rows(rows: List[List[str]]) -> List[List[str]]:
    groups = defaultdict(list)
    order = []
    for r in rows:
        author = r[0].strip() if r and r[0] else ""
        if author not in groups:
            order.append(author)
        groups[author].append(r)

    COLLISION_COL = 6

    yt_to_rows = defaultdict(list)
    bili_to_rows = defaultdict(list)
    for r in rows:
        yt_link = r[1].strip() if len(r) > 1 else ""
        bili_link = r[3].strip() if len(r) > 3 else ""
        if yt_link:
            yt_to_rows[yt_link].append(r)
        if bili_link:
            bili_to_rows[bili_link].append(r)

    for yt, rlist in yt_to_rows.items():
        if len(rlist) < 2:
            continue
        bili_set = set(r[3].strip() if len(r) > 3 else "" for r in rlist)
        if len(bili_set) > 1:
            for r in rlist:
                while len(r) <= COLLISION_COL:
                    r.append("")
                note = "同原视频不同B站"
                existing = r[COLLISION_COL]
                r[COLLISION_COL] = existing + "；" + note if existing else note

    for bili, rlist in bili_to_rows.items():
        if len(rlist) < 2:
            continue
        yt_set = set(r[1].strip() if len(r) > 1 else "" for r in rlist)
        if len(yt_set) > 1:
            for r in rlist:
                while len(r) <= COLLISION_COL:
                    r.append("")
                note = "不同原视频相同B站"
                existing = r[COLLISION_COL]
                r[COLLISION_COL] = existing + "；" + note if existing else note

    combined = []
    for author in order:
        if not author:
            combined.extend(groups[author])
            continue
        if combined:
            combined.append([])
        combined.extend(groups[author])
    return combined


# ==================== 7. 在线表格工具函数（共用） ====================
def _cell_value_to_text(cv) -> str:
    if not cv:
        return ""
    if "text" in cv:
        return cv["text"]
    if "link" in cv:
        return cv["link"].get("text") or cv["link"].get("url", "")
    if "location" in cv:
        return cv["location"].get("name", "")
    return ""


def _is_empty_api_row(row) -> bool:
    return all(_cell_value_to_text(cv).strip() == "" for cv in row)


def get_sheet_info(file_id: str, sheet_id: str):
    if not all([ACCESS_TOKEN, CLIENT_ID, OPEN_ID]):
        print("[警告] 缺少凭证，无法获取工作表信息")
        return 0, 0
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Client-Id": CLIENT_ID,
        "Open-Id": OPEN_ID,
    }
    url = f"https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"  [警告] GET files 返回 HTTP {resp.status_code}")
            return 0, 0
        data = resp.json()
        for p in data.get("properties", []):
            if str(p.get("sheetId")) == str(sheet_id):
                rc = int(p.get("rowCount", 0))
                rt = int(p.get("rowTotal", 0))
                print(
                    f"  [API] sheetId={p.get('sheetId')}, 标题={p.get('title','')}, rowCount={rc}, rowTotal={rt}"
                )
                return rc, rt
        print(f"  [警告] 未找到 sheetId={sheet_id}")
        return 0, 0
    except Exception as e:
        print(f"  [警告] GET files 异常: {e}")
        return 0, 0


def _fetch_all_api_rows(file_id: str, sheet_id: str, total_rows: int) -> list:
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Client-Id": CLIENT_ID,
        "Open-Id": OPEN_ID,
    }
    all_rows = []
    batch_size = 500
    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows) - 1
        if start > end:
            break
        range_str = f"A{start+1}:Z{end+1}"
        try:
            resp = requests.get(
                f"https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}/{sheet_id}/{range_str}",
                headers=headers,
                timeout=20,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            rows_data = data.get("gridData", {}).get("rows", [])
            for row_obj in rows_data:
                values = row_obj.get("values", [])
                row = [cell.get("cellValue", None) for cell in values]
                all_rows.append(row)
        except Exception:
            continue
    return all_rows


def find_last_content_row(file_id: str, sheet_id: str, row_count: int) -> int:
    if row_count == 0:
        return -1
    print("→ 正在扫描表格，定位最后有内容行（跳过空白行）...")
    rows = _fetch_all_api_rows(file_id, sheet_id, row_count)
    for i in range(len(rows) - 1, -1, -1):
        if not _is_empty_api_row(rows[i]):
            print(f"  最后有内容行: 第 {i + 1} 行（0-based: {i}）")
            return i
    print("  表格全空")
    return -1


# ==================== 8. 上传功能 ====================
def upload_to_tdocs(processed_rows: List[List[str]], config: dict, dry_run=False):
    file_id = config.get("file_id")
    sheet_id = config.get("sheet_id")
    if not file_id or not sheet_id:
        print("[错误] 配置缺少 file_id 或 sheet_id")
        return False

    if dry_run:
        start_row = 0
        print(f"\n[DRY RUN] 起始行: 第 1 行（0-based: 0）")
    else:
        row_count, _ = get_sheet_info(file_id, sheet_id)
        if row_count > 0:
            last_content = find_last_content_row(file_id, sheet_id, row_count)
            if last_content >= 0:
                start_row = last_content + 2
                print(f"→ 最后有内容行: 第 {last_content + 1} 行")
                print(
                    f"→ 将从第 {start_row + 1} 行开始追加（第 {last_content + 2} 行为空行）"
                )
            else:
                start_row = 0
                print("→ 表格全空，将从第 1 行开始写入")
        else:
            start_row = 0
            print("→ 表格为空，将从第 1 行开始写入")

    if not dry_run:
        if not all([ACCESS_TOKEN, CLIENT_ID, OPEN_ID]):
            print("[错误] 缺少认证信息")
            return False
        headers = {
            "Access-Token": ACCESS_TOKEN,
            "Client-Id": CLIENT_ID,
            "Open-Id": OPEN_ID,
            "Content-Type": "application/json",
        }
    else:
        headers = None

    grid_rows = []
    for row in processed_rows:
        if not row:
            grid_rows.append({"values": []})
        else:
            vals = []
            for i, cell in enumerate(row):
                cell = cell.strip()
                if cell.startswith(("http://", "https://")):
                    vals.append({"cellValue": {"link": {"url": cell, "text": cell}}})
                elif i == 4 and cell:
                    try:
                        num = float(cell)
                        vals.append({"cellValue": {"number": num}})
                    except ValueError:
                        vals.append({"cellValue": {"text": cell}})
                else:
                    vals.append({"cellValue": {"text": cell}})
            grid_rows.append({"values": vals})

    payload = {
        "requests": [
            {
                "updateRangeRequest": {
                    "sheetId": sheet_id,
                    "gridData": {
                        "startRow": start_row,
                        "startColumn": 0,
                        "rows": grid_rows,
                    },
                }
            }
        ]
    }

    if dry_run:
        print(f"  总行数: {len(grid_rows)}")
        print(
            f"  payload 前 300 字符: {json.dumps(payload, ensure_ascii=False)[:300]}..."
        )
        return True

    url = f"https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}/batchUpdate"
    print("→ 正在上传...")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"  响应: HTTP {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            if "responses" in body:
                has_error = False
                for r in body["responses"]:
                    if "error" in r:
                        err = r["error"]
                        print(
                            f"  子请求错误: code={err.get('code')}, msg={err.get('message')}"
                        )
                        has_error = True
                if has_error:
                    print(f"  完整响应: {json.dumps(body, ensure_ascii=False)}")
                    return False
                updated = (
                    body["responses"][0]
                    .get("updateRangeResponse", {})
                    .get("updatedCells", 0)
                )
                new_total = start_row + len(grid_rows)
                print(
                    f"✓ 成功上传 {len(grid_rows)} 行，更新了 {updated} 个单元格（新总行数: {new_total}）"
                )
                return True
            elif "code" in body and body.get("code") != 0:
                print(f"  业务错误: code={body.get('code')}, msg={body.get('message')}")
                return False
            else:
                print(f"  未知响应格式: {json.dumps(body, ensure_ascii=False)}")
                return False
        else:
            print(f"  响应体: {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"  请求异常: {e}")
        return False


# ==================== 9. 整理功能（原 order.py） ====================
# 以下函数全部基于原 order.py 逻辑，但复用公用工具函数
def clean_cell_urls(cv):
    """清理单元格内重复 URL，返回新 cellValue（不修改原对象）。"""
    if not cv:
        return cv
    if "link" in cv:
        link = cv["link"]
        text = link.get("text", "")
        if text and re.search(r"https?://", text):
            cleaned = _normalize_url_text(text)
            if cleaned != text:
                new_cv = copy.deepcopy(cv)
                new_cv["link"]["text"] = cleaned
                return new_cv
        return cv
    if "text" in cv:
        text = cv.get("text", "")
        if text and re.search(r"https?://", text):
            cleaned = _normalize_url_text(text)
            if cleaned != text:
                new_cv = copy.deepcopy(cv)
                new_cv["text"] = cleaned
                return new_cv
        return cv
    return cv


def _normalize_url_text(text: str) -> str:
    """拆分 URL 词条，去重后排序合并。"""
    if not text:
        return text.strip()
    tokens = text.split()
    urls = []
    non_urls = []
    for t in tokens:
        if re.match(r"https?://", t):
            urls.append(t)
        else:
            non_urls.append(t)
    unique_urls = sorted(set(urls))
    seen_non = list(dict.fromkeys(non_urls))
    return " ".join(unique_urls + seen_non)


def clean_row_cells(row):
    return [clean_cell_urls(cv) for cv in row]


def row_to_text_tuple(row) -> tuple:
    return tuple(_cell_value_to_text(cv).strip() for cv in row)


def deduplicate_in_groups(groups: dict, order: list) -> dict:
    deduped = {}
    total_removed = 0
    for author in order:
        rows = groups[author]
        seen = set()
        unique_rows = []
        for r in rows:
            key = row_to_text_tuple(r)
            if key in seen:
                total_removed += 1
                continue
            seen.add(key)
            unique_rows.append(r)
        deduped[author] = unique_rows
    if total_removed > 0:
        print(f"  ✓ 共去除 {total_removed} 行重复")
    else:
        print("  ✓ 未发现重复行")
    return deduped


def reorganize_rows(rows):
    """
    丢弃空行 → 按原作者分组 → 组内去重 → 组间插入空行占位符 None
    返回 (sorted_rows, max_columns)
    """
    groups = defaultdict(list)
    order_of_authors = []
    max_cols = 0
    for r in rows:
        if _is_empty_api_row(r):
            continue
        author = _cell_value_to_text(r[0]).strip() if r else "(空)"
        if author not in groups:
            order_of_authors.append(author)
        groups[author].append(r)
        max_cols = max(max_cols, len(r))

    print(
        f"  共 {len(order_of_authors)} 位作者，"
        f"原始数据行 {sum(len(groups[a]) for a in order_of_authors)} 行"
    )

    groups = deduplicate_in_groups(groups, order_of_authors)

    result = []
    for author in order_of_authors:
        grp = groups[author]
        if not grp:
            continue
        if result:
            result.append(None)  # 占位符 → 分隔空行
        result.extend(grp)

    return result, max_cols


def build_order_batch_requests(sheet_id, sorted_rows, num_columns, total_rows):
    """
    构造 batchUpdate 的 requests：
      1) 清空整个表格（全部行 × num_columns）
      2) 写入整理后的数据
    """
    reqs = []

    # 请求1：清空
    empty_rows = []
    for _ in range(total_rows):
        empty_row = [{"cellValue": {"text": ""}} for _ in range(num_columns)]
        empty_rows.append({"values": empty_row})
    reqs.append(
        {
            "updateRangeRequest": {
                "sheetId": sheet_id,
                "gridData": {
                    "startRow": 0,
                    "startColumn": 0,
                    "rows": empty_rows,
                },
            }
        }
    )

    # 请求2：写入整理后的数据
    data_rows = []
    for r in sorted_rows:
        if r is None:
            cols = [{"cellValue": {"text": ""}} for _ in range(num_columns)]
            data_rows.append({"values": cols})
        else:
            cols = []
            for i in range(num_columns):
                if i < len(r) and r[i] is not None:
                    cols.append({"cellValue": copy.deepcopy(r[i])})
                else:
                    cols.append({"cellValue": {"text": ""}})
            data_rows.append({"values": cols})
    reqs.append(
        {
            "updateRangeRequest": {
                "sheetId": sheet_id,
                "gridData": {
                    "startRow": 0,
                    "startColumn": 0,
                    "rows": data_rows,
                },
            }
        }
    )
    return reqs


def order_sheet(file_id, sheet_id, dry_run=False):
    """
    整理在线表格：下载 → 清理 URL → 去重 → 分组 → 空行分隔 → 清空+写入
    """
    if not all([ACCESS_TOKEN, CLIENT_ID, OPEN_ID]):
        print("[错误] 缺少认证信息，无法整理")
        return False

    # 1. 获取行数
    row_count, row_total = get_sheet_info(file_id, sheet_id)
    print(f"工作表当前行数: {row_count} (总上限: {row_total})")
    if row_count == 0:
        print("没有数据，无需整理")
        return True

    # 2. 下载全部数据
    print("→ 正在下载全部数据 ...")
    rows = _fetch_all_api_rows(file_id, sheet_id, row_count)
    print(f"  成功获取 {len(rows)} 行")

    # 3. 清理单元格内重复URL
    print("→ 正在清理单元格内重复URL ...")
    rows = [clean_row_cells(row) for row in rows]

    # 4. 整理：分组、去重、分隔
    print("→ 正在整理（分组 + 去重 + 分隔）...")
    sorted_rows, max_cols = reorganize_rows(rows)
    num_columns = max(max_cols, 8)  # 至少保证8列

    data_rows = sum(1 for r in sorted_rows if r is not None)
    sep_rows = sum(1 for r in sorted_rows if r is None)
    print(
        f"  整理后: {len(sorted_rows)} 行"
        f"（数据 {data_rows} 行 + 分隔空行 {sep_rows} 行）"
    )

    # 5. 构造请求并写回
    batch_reqs = build_order_batch_requests(
        sheet_id, sorted_rows, num_columns, row_count
    )
    payload = {"requests": batch_reqs}
    clear_rows = row_count - len(sorted_rows)
    print(f"  将清空全部 {row_count} 行，写入 {len(sorted_rows)} 行")
    print(f"→ 正在发送 batchUpdate ({len(batch_reqs)} 个请求)...")

    if dry_run:
        print(f"\n[DRY RUN] 整理后 {len(sorted_rows)} 行（原 {row_count} 行）")
        print("  预览：")
        for i, r in enumerate(sorted_rows):
            if r is None:
                print(f"    {i+1}: (空行)")
            else:
                author = _cell_value_to_text(r[0])[:20]
                urls_raw = _cell_value_to_text(r[1]) if len(r) > 1 else ""
                urls_disp = urls_raw[:60] + ("..." if len(urls_raw) > 60 else "")
                print(f"    {i+1}: {author} | {urls_disp}")
            if i >= 9 and len(sorted_rows) > 10:
                print(f"    ... 共 {len(sorted_rows)} 行")
                break
        return True

    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Client-Id": CLIENT_ID,
        "Open-Id": OPEN_ID,
        "Content-Type": "application/json",
    }
    url = f"https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}/batchUpdate"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            body = resp.json()
            if "responses" in body:
                errors = [r.get("error") for r in body["responses"] if "error" in r]
                if errors:
                    print(f"  部分错误: {json.dumps(errors, ensure_ascii=False)[:500]}")
                    return False
                updated = sum(
                    r.get("updateRangeResponse", {}).get("updatedCells", 0)
                    for r in body["responses"]
                )
                print(f"✓ 整理完成，更新了 {updated} 个单元格")
                return True
            elif "code" in body and body.get("code") != 0:
                print(f"  错误: {body.get('code')} - {body.get('message')}")
                return False
            else:
                print(f"  未知响应: {json.dumps(body, ensure_ascii=False)[:300]}")
                return False
        else:
            print(f"  请求失败 HTTP {resp.status_code}: {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"  请求异常: {e}")
        return False


# ==================== 10. 主流程 ====================
def main():
    (
        check_only,
        upload_only,
        order_only,
        dry_run,
        file_id_override,
        sheet_id_override,
    ) = parse_args()

    # 如果指定了 file_id/sheet_id 且运行 order_only，则用指定的覆盖配置
    if order_only:
        if file_id_override and sheet_id_override:
            file_id = file_id_override
            sheet_id = sheet_id_override
        else:
            cfg = load_upload_config()
            file_id = cfg.get("file_id")
            sheet_id = cfg.get("sheet_id")
        if not file_id or not sheet_id:
            print("[错误] 缺少 file_id 或 sheet_id")
            sys.exit(1)

        print("→ 模式：仅整理在线表格")
        success = order_sheet(file_id, sheet_id, dry_run)
        if success and not dry_run:
            print("\n✅ 整理完成")
        elif dry_run:
            print("\n[试运行结束，未实际修改表格]")
        else:
            print("\n❌ 整理失败")
            sys.exit(1)
        return

    # 以下是原 upload 模式的流程（含 check-only / upload-only）
    if upload_only:
        print("→ 模式：仅上传已有的 combined CSV")
        upload_cfg = load_upload_config()
        csv_dir = upload_cfg.get("csv_dir", "output")
        today_str = datetime.now().strftime("%Y%m%d")
        combined_path = Path(csv_dir) / f"combined-{today_str}.csv"
        if not combined_path.exists():
            print(f"[错误] 未找到 {combined_path}，请先运行本地处理")
            sys.exit(1)
        rows = read_csv(combined_path)
        rows = trim_empty_first_column(rows)
        print(f"→ 读取到 {len(rows)} 行（含空行）")
        ok = upload_to_tdocs(rows, upload_cfg, dry_run=dry_run)
        if ok and not dry_run:
            print("\n[上传成功]")
            # 上传后自动整理
            print("\n→ 正在自动整理表格 ...")
            fid = upload_cfg.get("file_id")
            sid = upload_cfg.get("sheet_id")
            if fid and sid:
                order_sheet(fid, sid, dry_run=False)
            else:
                print("[警告] 缺少 file_id/sheet_id，无法自动整理")
        elif dry_run:
            print("\n[试运行结束]")
        else:
            print("\n[上传失败]")
            sys.exit(1)
        return

    print("→ 模式：本地整理" + (" (仅本地)" if check_only else " + 上传"))
    upload_cfg = load_upload_config()
    time_range_str = get_time_range(upload_cfg)
    csv_dir_name = upload_cfg.get("csv_dir", "output")
    csv_dir_path = Path(csv_dir_name)

    if not csv_dir_path.exists():
        print(f"[错误] CSV 目录不存在: {csv_dir_path}")
        sys.exit(1)

    target_dates = get_target_dates(time_range_str)
    print(
        f"→ 时间范围: {time_range_str} → {target_dates if target_dates else '全部文件'}"
    )

    all_csv = [
        f for f in csv_dir_path.glob("*.csv") if not f.name.startswith("combined-")
    ]
    if not all_csv:
        print(f"[错误] 目录 {csv_dir_path} 下没有 CSV 文件")
        sys.exit(1)

    selected_files = []
    if target_dates:
        for f in all_csv:
            if any(d in f.name for d in target_dates):
                selected_files.append(f)
        if not selected_files:
            print(f"[错误] 未找到包含日期 {target_dates} 的 CSV 文件")
            sys.exit(1)
    else:
        selected_files = all_csv

    print(f"→ 匹配到 {len(selected_files)} 个文件:")
    for f in selected_files:
        print(f"  {f.name}")

    all_rows = []
    for f in selected_files:
        raw = read_csv(f)
        clean = trim_empty_first_column(raw)
        print(f"  {f.name}: {len(raw)} 行 → 清洗后 {len(clean)} 行")
        all_rows.extend(clean)

    if not all_rows:
        print("[提示] 没有有效数据，退出")
        return
    print(f"→ 共读取清洗后数据 {len(all_rows)} 行")

    unique_rows = deduplicate(all_rows)
    print(f"→ 去除了 {len(all_rows) - len(unique_rows)} 个完全相同的行")

    processed = process_rows(unique_rows)
    print(f"→ 整理后得到 {len(processed)} 行（含分隔空行）")

    today_str = datetime.now().strftime("%Y%m%d")
    out_dir = csv_dir_path
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"combined-{today_str}.csv"
    with open(out_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for row in processed:
            writer.writerow(row if row else [])
    print(f"→ 整理后的 CSV 已保存: {out_file}")

    if check_only:
        print("\n[仅本地处理，不上传]")
        return

    print("\n→ 开始上传...")
    ok = upload_to_tdocs(processed, upload_cfg, dry_run=dry_run)
    if ok and not dry_run:
        print("\n[上传成功]")
        # 上传后自动整理
        print("\n→ 正在自动整理表格 ...")
        fid = upload_cfg.get("file_id")
        sid = upload_cfg.get("sheet_id")
        if fid and sid:
            order_sheet(fid, sid, dry_run=False)
        else:
            print("[警告] 缺少 file_id/sheet_id，无法自动整理")
    elif dry_run:
        print("\n[试运行结束]")
    else:
        print("\n[上传失败]")
        sys.exit(1)


if __name__ == "__main__":
    main()
