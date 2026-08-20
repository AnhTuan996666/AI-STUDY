"""Client tối giản cho Ollama HTTP API (đồng bộ).

Tham chiếu API: POST /api/chat, GET /api/tags
- stream=False -> trả 1 JSON object duy nhất
- stream=True  -> trả NDJSON, mỗi dòng là 1 JSON object
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

from ollama_lab.config import Settings, load_settings

Message = dict[str, str]


class OllamaError(RuntimeError):
    """Lỗi khi giao tiếp với Ollama (không kết nối được, HTTP lỗi, JSON hỏng)."""


@dataclass
class ChatChunk:
    """Một mẩu nội dung trong luồng streaming."""

    content: str
    done: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResult:
    """Kết quả trả về đầy đủ của một lượt chat."""

    content: str
    model: str
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None or self.completion_tokens is None:
            return None
        return self.prompt_tokens + self.completion_tokens


class OllamaClient:
    """Bọc các lời gọi HTTP tới Ollama.

    Cho phép truyền sẵn `http_client` để test bằng httpx.MockTransport.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=self.settings.base_url,
            timeout=self.settings.timeout_seconds,
        )

    # --- lifecycle -------------------------------------------------------

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> OllamaClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # --- health / metadata ----------------------------------------------

    def is_alive(self) -> bool:
        """True nếu Ollama đang chạy và trả lời được."""
        try:
            self._http.get("/api/tags")
        except httpx.HTTPError:
            return False
        return True

    def list_models(self) -> list[str]:
        """Danh sách tên model đã pull về máy."""
        payload = self._get_json("/api/tags")
        return [m["name"] for m in payload.get("models", [])]

    # --- chat ------------------------------------------------------------

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        """Gọi model, chờ trả lời đầy đủ (không streaming)."""
        model_name = model or self.settings.model
        started = time.perf_counter()
        payload = self._post_json(
            "/api/chat",
            {
                "model": model_name,
                "messages": list(messages),
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        return ChatResult(
            content=payload.get("message", {}).get("content", ""),
            model=payload.get("model", model_name),
            latency_ms=latency_ms,
            prompt_tokens=payload.get("prompt_eval_count"),
            completion_tokens=payload.get("eval_count"),
        )

    def chat_stream(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Iterator[ChatChunk]:
        """Gọi model và yield từng mẩu nội dung ngay khi nhận được."""
        model_name = model or self.settings.model
        body = {
            "model": model_name,
            "messages": list(messages),
            "stream": True,
            "options": {"temperature": temperature},
        }

        try:
            with self._http.stream("POST", "/api/chat", json=body) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    chunk = _parse_chunk(line)
                    if chunk is not None:
                        yield chunk
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama trả về HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Không kết nối được Ollama: {exc}") from exc

    # --- internals -------------------------------------------------------

    def _get_json(self, path: str) -> dict[str, Any]:
        try:
            response = self._http.get(path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"GET {path} -> HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Không kết nối được Ollama: {exc}") from exc

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.post(path, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"POST {path} -> HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Không kết nối được Ollama: {exc}") from exc


def _parse_chunk(line: str) -> ChatChunk | None:
    """Chuyển 1 dòng NDJSON thành ChatChunk; bỏ qua dòng hỏng."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    if error := data.get("error"):
        raise OllamaError(str(error))

    return ChatChunk(
        content=data.get("message", {}).get("content", ""),
        done=bool(data.get("done", False)),
        raw=data,
    )
