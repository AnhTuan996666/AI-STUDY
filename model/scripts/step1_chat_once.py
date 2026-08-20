"""Mốc 2 — Gọi model bằng Python, KHÔNG streaming (chờ trả lời đầy đủ).

Chạy: python scripts/step1_chat_once.py "câu hỏi của bạn"
"""

from __future__ import annotations

import sys

from _bootstrap import bootstrap

bootstrap()

from ollama_lab import OllamaClient, OllamaError  # noqa: E402

DEFAULT_PROMPT = "Giải thích REST API trong đúng 3 câu, bằng tiếng Việt."
SYSTEM_PROMPT = "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn bằng tiếng Việt."


def main() -> int:
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    print(f"> {prompt}")
    print("-" * 48)
    print("Đang chờ model trả lời (không streaming)...\n")

    try:
        with OllamaClient() as client:
            result = client.chat(messages)
    except OllamaError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(result.content)
    print("-" * 48)
    print(f"model            : {result.model}")
    print(f"latency          : {result.latency_ms} ms")
    print(f"prompt tokens    : {result.prompt_tokens}")
    print(f"completion tokens: {result.completion_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
