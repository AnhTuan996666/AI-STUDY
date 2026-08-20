"""Test OllamaProvider bằng httpx.MockTransport — không cần Ollama thật."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.exceptions import LLMUnavailableError
from app.modules.chat.schemas import ChatMessage
from app.modules.llm.providers.ollama import OllamaProvider

MESSAGES = [ChatMessage(role="user", content="Xin chào")]


def _provider(handler) -> OllamaProvider:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    return OllamaProvider(base_url="http://ollama.test", model="qwen2.5:7b", http_client=http)


@pytest.mark.asyncio
async def test_health_true_when_tags_ok() -> None:
    provider = _provider(lambda _r: httpx.Response(200, json={"models": []}))
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_health_false_on_connect_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = _provider(handler)
    assert await provider.health() is False


@pytest.mark.asyncio
async def test_generate_maps_ollama_payload() -> None:
    payload = {
        "model": "qwen2.5:7b",
        "message": {"role": "assistant", "content": "Chào bạn!"},
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 4,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["messages"][0]["content"] == "Xin chào"
        return httpx.Response(200, json=payload)

    result = await _provider(handler).generate(MESSAGES)

    assert result.content == "Chào bạn!"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 4


@pytest.mark.asyncio
async def test_generate_raises_llm_unavailable_on_connect_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMUnavailableError):
        await _provider(handler).generate(MESSAGES)


@pytest.mark.asyncio
async def test_generate_raises_on_http_500() -> None:
    with pytest.raises(LLMUnavailableError):
        await _provider(lambda _r: httpx.Response(500, text="boom")).generate(MESSAGES)


@pytest.mark.asyncio
async def test_stream_yields_chunks_and_final_usage() -> None:
    ndjson = "\n".join(
        json.dumps(item)
        for item in [
            {"message": {"content": "Chào "}, "done": False},
            {"message": {"content": "bạn"}, "done": False},
            {"message": {"content": ""}, "done": True, "eval_count": 2},
        ]
    )

    provider = _provider(lambda _r: httpx.Response(200, text=ndjson))
    chunks = [c async for c in provider.stream(MESSAGES)]

    assert "".join(c.content for c in chunks) == "Chào bạn"
    assert chunks[-1].done is True
    assert chunks[-1].completion_tokens == 2


@pytest.mark.asyncio
async def test_stream_raises_on_error_line() -> None:
    ndjson = json.dumps({"error": "model 'x' not found"})
    provider = _provider(lambda _r: httpx.Response(200, text=ndjson))

    with pytest.raises(LLMUnavailableError, match="not found"):
        [c async for c in provider.stream(MESSAGES)]
