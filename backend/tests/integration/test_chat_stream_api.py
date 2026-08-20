"""Test mốc 5 — POST /api/v1/chat/stream (SSE)."""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient


def _read_events(client: TestClient, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Đọc toàn bộ SSE frame và parse thành list dict."""
    events: list[dict[str, Any]] = []
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def test_stream_returns_deltas_then_done(client: TestClient) -> None:
    events = _read_events(client, {"messages": [{"role": "user", "content": "Đếm từ 1 đến 5"}]})

    assert len(events) > 1
    assert all(e["type"] == "delta" for e in events[:-1])
    assert events[-1]["type"] == "done"


def test_stream_deltas_reassemble_into_full_answer(client: TestClient) -> None:
    events = _read_events(
        client, {"messages": [{"role": "user", "content": "kiểm tra ghép chuỗi"}]}
    )

    full = "".join(e["content"] for e in events if e["type"] == "delta")
    assert "kiểm tra ghép chuỗi" in full
    assert full.startswith("[MOCK]")


def test_stream_done_event_carries_metadata(client: TestClient) -> None:
    events = _read_events(client, {"messages": [{"role": "user", "content": "hi"}]})

    done = events[-1]
    assert done["model"] == "mock-model"
    assert done["latency_ms"] >= 0
    assert done["usage"]["completion_tokens"] > 0


def test_stream_sse_no_buffering_headers(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    ) as response:
        assert response.headers["x-accel-buffering"] == "no"
        assert "no-cache" in response.headers["cache-control"]
        response.read()


def test_stream_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post("/api/v1/chat/stream", json={"messages": []})
    assert response.status_code == 422
