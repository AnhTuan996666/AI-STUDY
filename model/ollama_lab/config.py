"""Cấu hình cho lớp model, đọc từ biến môi trường / file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class Settings:
    """Cấu hình bất biến cho một phiên làm việc."""

    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


def load_settings() -> Settings:
    """Nạp .env (nếu có) rồi dựng Settings từ biến môi trường."""
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)

    return Settings(
        base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        model=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
        timeout_seconds=float(
            os.getenv("OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        ),
    )
