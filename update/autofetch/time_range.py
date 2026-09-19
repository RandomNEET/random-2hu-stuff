import argparse
import re
from datetime import datetime


def parse_time_range(value: str) -> str | int:
    """解析 today、all、YYYYMMDD 或正整数自然日范围。"""
    normalized = value.strip().lower()
    if normalized in {"today", "all"}:
        return normalized
    if re.fullmatch(r"\d{8}", normalized):
        try:
            datetime.strptime(normalized, "%Y%m%d")
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"无效日期: {value}") from e
        return normalized
    try:
        days = int(normalized)
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            "时间范围必须是 today、all、YYYYMMDD 或正整数"
        ) from e
    if days < 1:
        raise argparse.ArgumentTypeError("天数必须大于 0")
    return days
