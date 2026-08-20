"""Mốc 0 — Kiểm tra Ollama đã sống chưa và liệt kê model có sẵn.

Chạy: python scripts/step0_check.py
"""

from __future__ import annotations

import sys

from _bootstrap import bootstrap

bootstrap()

from ollama_lab import OllamaClient, OllamaError, load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    print(f"Ollama base URL : {settings.base_url}")
    print(f"Model mặc định  : {settings.model}")
    print("-" * 48)

    with OllamaClient(settings) as client:
        if not client.is_alive():
            print("[FAIL] Không kết nối được Ollama.")
            print("       -> Cài Ollama: https://ollama.com/download/windows")
            print("       -> Hoặc khởi động: ollama serve")
            return 1

        print("[OK] Ollama đang chạy.")

        try:
            models = client.list_models()
        except OllamaError as exc:
            print(f"[FAIL] {exc}")
            return 1

        if not models:
            print("[WARN] Chưa có model nào. Chạy: ollama pull qwen2.5:7b")
            return 1

        print(f"[OK] Có {len(models)} model:")
        for name in models:
            marker = " <- mặc định" if name == settings.model else ""
            print(f"     - {name}{marker}")

        if settings.model not in models:
            print(f"[WARN] Model '{settings.model}' chưa được pull.")
            print(f"       -> ollama pull {settings.model}")
            return 1

    print("-" * 48)
    print("[DONE] Sẵn sàng cho mốc 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
