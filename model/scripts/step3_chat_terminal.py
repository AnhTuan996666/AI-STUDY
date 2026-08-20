"""Mốc 1 (bản Python) — Chat REPL nhiều lượt trên terminal, có nhớ ngữ cảnh.

Chạy: python scripts/step3_chat_terminal.py
Lệnh trong REPL: /reset (xóa ngữ cảnh), /history (xem lịch sử), /exit (thoát)
"""

from __future__ import annotations

import sys

from _bootstrap import bootstrap

bootstrap()

from ollama_lab import OllamaClient, OllamaError  # noqa: E402

SYSTEM_PROMPT = "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn và chính xác bằng tiếng Việt."
BANNER = """
=================================================
 AI Chat - Terminal (Ollama)
 /reset   xóa ngữ cảnh
 /history xem lịch sử
 /exit    thoát
=================================================
"""


def _new_history() -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def main() -> int:
    client = OllamaClient()
    if not client.is_alive():
        print("[FAIL] Ollama chưa chạy. Xem REMIND.md mục 0.")
        client.close()
        return 1

    print(BANNER)
    print(f"Model: {client.settings.model}\n")

    history = _new_history()

    try:
        while True:
            try:
                user_input = input("Bạn > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nTạm biệt.")
                return 0

            if not user_input:
                continue

            if user_input in {"/exit", "/quit"}:
                print("Tạm biệt.")
                return 0

            if user_input == "/reset":
                history = _new_history()
                print("(đã xóa ngữ cảnh)\n")
                continue

            if user_input == "/history":
                for msg in history[1:]:
                    print(f"  [{msg['role']}] {msg['content'][:80]}")
                print()
                continue

            history.append({"role": "user", "content": user_input})

            print("AI  > ", end="", flush=True)
            answer_parts: list[str] = []
            try:
                for chunk in client.chat_stream(history):
                    if chunk.content:
                        print(chunk.content, end="", flush=True)
                        answer_parts.append(chunk.content)
            except OllamaError as exc:
                print(f"\n[LỖI] {exc}\n")
                history.pop()
                continue

            print("\n")
            history.append({"role": "assistant", "content": "".join(answer_parts)})
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
