"""Test mốc 4 — POST /api/v1/chat (không streaming)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_chat_returns_answer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "Xin chào"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Xin chào" in body["content"]
    assert body["model"] == "mock-model"
    assert body["latency_ms"] >= 0
    assert body["usage"]["total_tokens"] >= 0


def test_chat_rejects_empty_messages(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"messages": []})
    assert response.status_code == 422


def test_chat_rejects_empty_content(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": ""}]},
    )
    assert response.status_code == 422


def test_chat_rejects_invalid_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "hacker", "content": "hi"}]},
    )
    assert response.status_code == 422


def test_chat_rejects_out_of_range_temperature(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 9.5,
        },
    )
    assert response.status_code == 422


def test_chat_uses_last_user_message_as_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {"role": "user", "content": "câu đầu"},
                {"role": "assistant", "content": "trả lời"},
                {"role": "user", "content": "câu cuối"},
            ]
        },
    )

    assert response.status_code == 200
    assert "câu cuối" in response.json()["content"]


def test_cors_headers_present_for_allowed_origin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
