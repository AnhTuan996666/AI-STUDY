"""Smoke test end-to-end cho backend đang chạy.

Kiểm tra: /health, POST /chat, POST /chat/stream (có xác nhận dữ liệu về DẦN
chứ không phải một cục).

Chạy:
    backend\\.venv\\Scripts\\python.exe scripts\\smoke_test.py
    backend\\.venv\\Scripts\\python.exe scripts\\smoke_test.py http://localhost:8000
"""

from __future__ import annotations

import json
import sys
import time

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PREFIX = "/api/v1"
PASS = "[PASS]"
FAIL = "[FAIL]"


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL).rstrip("/")
    print(f"Backend: {base_url}\n" + "=" * 56)

    failures = 0
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        failures += _check_health(client)
        failures += _check_chat(client)
        failures += _check_stream(client)

    print("=" * 56)
    if failures:
        print(f"{FAIL} {failures} kiểm tra thất bại.")
        return 1

    print(f"{PASS} Tất cả kiểm tra đều đạt.")
    return 0


def _check_health(client: httpx.Client) -> int:
    print("\n[1/3] GET /health")
    try:
        response = client.get(f"{PREFIX}/health")
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        print(f"  {FAIL} Không gọi được backend: {exc}")
        return 1

    print(f"  status        : {data['status']}")
    print(f"  provider      : {data['llm_provider']}")
    print(f"  model         : {data['model']}")
    print(f"  llm_reachable : {data['llm_reachable']}")

    if not data["llm_reachable"]:
        print(f"  {FAIL} Model server chưa sẵn sàng (bật Ollama hoặc LLM_PROVIDER=mock).")
        return 1

    print(f"  {PASS}")
    return 0


def _check_chat(client: httpx.Client) -> int:
    print("\n[2/3] POST /chat (không streaming)")
    payload = {"messages": [{"role": "user", "content": "Xin chào, đây là smoke test."}]}

    try:
        response = client.post(f"{PREFIX}/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        print(f"  {FAIL} {exc}")
        return 1

    preview = data["content"][:90].replace("\n", " ")
    print(f"  latency : {data['latency_ms']} ms")
    print(f"  usage   : {data['usage']}")
    print(f"  content : {preview}...")

    if not data["content"].strip():
        print(f"  {FAIL} Nội dung trả về rỗng.")
        return 1

    print(f"  {PASS}")
    return 0


def _check_stream(client: httpx.Client) -> int:
    print("\n[3/3] POST /chat/stream (SSE)")
    payload = {"messages": [{"role": "user", "content": "Đếm từ 1 đến 10."}]}

    started = time.perf_counter()
    first_delta_ms: int | None = None
    last_delta_ms = 0
    deltas: list[str] = []
    done_event: dict | None = None
    error_event: dict | None = None

    try:
        with client.stream("POST", f"{PREFIX}/chat/stream", json=payload) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("text/event-stream"):
                print(f"  {FAIL} content-type sai: {content_type}")
                return 1

            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue

                event = json.loads(line[len("data: ") :])
                elapsed = int((time.perf_counter() - started) * 1000)

                if event["type"] == "delta":
                    if first_delta_ms is None:
                        first_delta_ms = elapsed
                    last_delta_ms = elapsed
                    deltas.append(event["content"])
                elif event["type"] == "done":
                    done_event = event
                elif event["type"] == "error":
                    error_event = event
    except httpx.HTTPError as exc:
        print(f"  {FAIL} {exc}")
        return 1

    if error_event:
        print(f"  {FAIL} Backend báo lỗi: {error_event['message']}")
        return 1

    full = "".join(deltas)
    spread_ms = last_delta_ms - (first_delta_ms or 0)

    print(f"  số chunk         : {len(deltas)}")
    print(f"  first token      : {first_delta_ms} ms")
    print(f"  tổng thời gian   : {last_delta_ms} ms")
    print(f"  khoảng trải chunk: {spread_ms} ms")
    print(f"  ký tự nhận được  : {len(full)}")
    print(f"  nội dung         : {full[:90].replace(chr(10), ' ')}...")

    if len(deltas) < 2:
        print(f"  {FAIL} Chỉ nhận được {len(deltas)} chunk -> không phải streaming thật.")
        return 1

    if done_event is None:
        print(f"  {FAIL} Thiếu sự kiện 'done' kết thúc luồng.")
        return 1

    print(f"  done event       : model={done_event.get('model')} usage={done_event.get('usage')}")
    print(f"  {PASS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
