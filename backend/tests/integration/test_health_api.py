"""Test endpoint health và root."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/api/v1/health"


def test_health_ok_with_mock_provider(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "mock"
    assert body["llm_reachable"] is True


def test_openapi_documents_chat_endpoints(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/v1/chat" in schema["paths"]
    assert "/api/v1/chat/stream" in schema["paths"]
