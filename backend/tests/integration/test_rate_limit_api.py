"""Test FR-09 — rate limit ở mức HTTP."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def limited_client() -> Iterator[TestClient]:
    settings = Settings(
        app_env="test",
        llm_provider="mock",
        rate_limit_enabled=True,
        rate_limit_requests=3,
        rate_limit_window_seconds=60,
        log_level="WARNING",
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_chat_returns_429_after_limit(limited_client: TestClient) -> None:
    payload = {"messages": [{"role": "user", "content": "hi"}]}

    for _ in range(3):
        assert limited_client.post("/api/v1/chat", json=payload).status_code == 200

    blocked = limited_client.post("/api/v1/chat", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
    assert blocked.headers["retry-after"] == "60"


def test_remaining_header_counts_down(limited_client: TestClient) -> None:
    payload = {"messages": [{"role": "user", "content": "hi"}]}

    first = limited_client.post("/api/v1/chat", json=payload)
    second = limited_client.post("/api/v1/chat", json=payload)

    assert first.headers["x-ratelimit-limit"] == "3"
    assert first.headers["x-ratelimit-remaining"] == "2"
    assert second.headers["x-ratelimit-remaining"] == "1"


def test_health_is_not_rate_limited(limited_client: TestClient) -> None:
    for _ in range(10):
        assert limited_client.get("/api/v1/health").status_code == 200
