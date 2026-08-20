"""Test OllamaClient bằng httpx.MockTransport — không cần Ollama thật."""

from __future__ import annotations

import json

import httpx
import pytest

from ollama_lab import ChatChunk, OllamaClient, OllamaError, Settings

SETTINGS = Settings(base_url="http://ollama.test", model="test-model", timeout_seconds=5)


def _client(handler) -> OllamaClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url=SETTINGS.base_url)
    return OllamaClient(SETTINGS, http_client=http)


def test_is_alive_true_when_tags_ok() -> None:
    with _client(lambda _req: httpx.Response(200, json={"models": []})) as client:
        assert client.is_alive() is True


def test_is_alive_false_on_connect_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with _client(handler) as client:
        assert client.is_alive() is False


def test_list_models_returns_names() -> None:
    payload = {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.1:8b"}]}
    with _client(lambda _req: httpx.Response(200, json=payload)) as client:
        assert client.list_models() == ["qwen2.5:7b", "llama3.1:8b"]


def test_chat_returns_content_and_usage() -> None:
    payload = {
        "model": "test-model",
        "message": {"role": "assistant", "content": "Xin chào!"},
        "done": True,
        "prompt_eval_count": 12,
        "eval_count": 7,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["model"] == "test-model"
        return httpx.Response(200, json=payload)

    with _client(handler) as client:
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result.content == "Xin chào!"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 7
    assert result.total_tokens == 19
    assert result.latency_ms >= 0


def test_chat_raises_on_http_error() -> None:
    with (
        _client(lambda _req: httpx.Response(500, json={"error": "boom"})) as client,
        pytest.raises(OllamaError),
    ):
        client.chat([{"role": "user", "content": "hi"}])


def test_chat_stream_yields_chunks_in_order() -> None:
    lines = [
        {"message": {"content": "Xin "}, "done": False},
        {"message": {"content": "chào"}, "done": False},
        {"message": {"content": ""}, "done": True, "eval_count": 3},
    ]
    ndjson = "\n".join(json.dumps(item) for item in lines)

    with _client(lambda _req: httpx.Response(200, text=ndjson)) as client:
        chunks: list[ChatChunk] = list(
            client.chat_stream([{"role": "user", "content": "hi"}])
        )

    assert [c.content for c in chunks] == ["Xin ", "chào", ""]
    assert chunks[-1].done is True
    assert "".join(c.content for c in chunks) == "Xin chào"


def test_chat_stream_skips_broken_lines() -> None:
    ndjson = "\n".join(
        [
            json.dumps({"message": {"content": "ok"}, "done": False}),
            "{not json",
            json.dumps({"message": {"content": ""}, "done": True}),
        ]
    )

    with _client(lambda _req: httpx.Response(200, text=ndjson)) as client:
        chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))

    assert [c.content for c in chunks] == ["ok", ""]


def test_chat_stream_raises_on_error_field() -> None:
    ndjson = json.dumps({"error": "model not found"})

    with (
        _client(lambda _req: httpx.Response(200, text=ndjson)) as client,
        pytest.raises(OllamaError, match="model not found"),
    ):
        list(client.chat_stream([{"role": "user", "content": "hi"}]))
