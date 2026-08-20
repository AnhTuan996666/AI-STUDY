"""Mốc 3 — Gọi model có STREAMING, in dần từng token + đo time-to-first-token.

Chạy: python scripts/step2_chat_stream.py "câu hỏi của bạn"
"""

from __future__ import annotations

import sys
import time

from _bootstrap import bootstrap

bootstrap()

from ollama_lab import OllamaClient, OllamaError  # noqa: E402

DEFAULT_PROMPT = "Viết một đoạn văn khoảng 100 từ về trí tuệ nhân tạo."
SYSTEM_PROMPT = "Bạn là trợ lý AI hữu ích, trả lời bằng tiếng Việt."


def main() -> int:
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    print(f"> {prompt}")
    print("-" * 48)

    started = time.perf_counter()
    first_token_ms: int | None = None
    chunk_count = 0
    char_count = 0

    try:
        with OllamaClient() as client:
            for chunk in client.chat_stream(messages):
                if chunk.content:
                    if first_token_ms is None:
                        first_token_ms = int((time.perf_counter() - started) * 1000)
                    print(chunk.content, end="", flush=True)
                    chunk_count += 1
                    char_count += len(chunk.content)
    except OllamaError as exc:
        print(f"\n[FAIL] {exc}")
        return 1

    total_ms = int((time.perf_counter() - started) * 1000)
    print("\n" + "-" * 48)
    print(f"time to first token : {first_token_ms} ms")
    print(f"total time          : {total_ms} ms")
    print(f"chunks              : {chunk_count}")
    print(f"characters          : {char_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
