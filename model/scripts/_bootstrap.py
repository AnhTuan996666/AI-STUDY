"""Cho phép chạy `python scripts/xxx.py` mà vẫn import được package `ollama_lab`."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> None:
    """Thêm thư mục gốc của model layer vào sys.path."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
