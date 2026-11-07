"""Shared .env loading; existing process environment takes precedence."""

import os
from pathlib import Path


def load_dotenv(dotenv_path: Path = Path("config/.env"), *, quiet=False):
    if not dotenv_path.exists():
        if not quiet:
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
