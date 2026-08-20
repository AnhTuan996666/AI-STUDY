"""Provider gọi Ollama qua HTTP (async)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from app.core.exceptions import LLMUnavailableError
from app.core.logging import get_logger
from app.modules.chat.schemas import ChatMessage
from app.modules.llm.providers.base import LLMChunk, LLMModel, LLMProvider, LLMResult

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Bọc Ollama HTTP API: /api/tags và /api/chat."""

    name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds, connect=10.0),
        )

    @property
    def default_model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def health(self) -> bool:
        try:
            response = await self._http.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[LLMModel]:
        """Đọc `GET /api/tags` của Ollama.

        Ollama chết thì trả list rỗng thay vì ném lỗi: thiếu danh sách model chỉ làm
        menu chọn rỗng, không đáng để làm hỏng cả màn hình.
        """
        try:
            response = await self._http.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("Không lấy được danh sách model từ Ollama.")
            return []

        return [_parse_model(item) for item in payload.get("models", []) if item.get("model")]

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResult:
        model_name = model or self._model
        body = _build_body(messages, model_name, temperature, stream=False)

        try:
            response = await self._http.post("/api/chat", json=body)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMUnavailableError(
                f"Model server trả về HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                "Không kết nối được model server (Ollama). Kiểm tra Ollama đã chạy chưa."
            ) from exc

        if error := payload.get("error"):
            raise LLMUnavailableError(str(error))

        return LLMResult(
            content=payload.get("message", {}).get("content", ""),
            model=payload.get("model", model_name),
            prompt_tokens=payload.get("prompt_eval_count"),
            completion_tokens=payload.get("eval_count"),
        )

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]:
        model_name = model or self._model
        body = _build_body(messages, model_name, temperature, stream=True)

        try:
            async with self._http.stream("POST", "/api/chat", json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = _parse_line(line)
                    if chunk is not None:
                        yield chunk
        except httpx.HTTPStatusError as exc:
            raise LLMUnavailableError(
                f"Model server trả về HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError("Mất kết nối tới model server trong lúc streaming.") from exc


def _parse_model(item: dict[str, Any]) -> LLMModel:
    """Chuyển 1 phần tử trong `/api/tags` sang khuôn chung."""
    model_id = str(item["model"])
    details = item.get("details") or {}
    parts = [
        details.get("parameter_size"),
        details.get("quantization_level"),
        details.get("family"),
    ]
    description = " · ".join(str(p) for p in parts if p) or None

    size = item.get("size")
    return LLMModel(
        id=model_id,
        name=item.get("name") or model_id,
        description=description,
        size_bytes=int(size) if isinstance(size, int | float) else None,
    )


def _build_body(
    messages: Sequence[ChatMessage],
    model: str,
    temperature: float,
    *,
    stream: bool,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "stream": stream,
        "options": {"temperature": temperature},
    }


def _parse_line(line: str) -> LLMChunk | None:
    """Chuyển 1 dòng NDJSON của Ollama thành LLMChunk. Dòng hỏng -> bỏ qua."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        logger.debug("Bỏ qua dòng NDJSON không hợp lệ: %r", line[:120])
        return None

    if error := data.get("error"):
        raise LLMUnavailableError(str(error))

    return LLMChunk(
        content=data.get("message", {}).get("content", ""),
        done=bool(data.get("done", False)),
        prompt_tokens=data.get("prompt_eval_count"),
        completion_tokens=data.get("eval_count"),
    )
