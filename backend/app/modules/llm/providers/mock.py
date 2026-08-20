"""Provider giả lập — dùng khi chưa cài Ollama hoặc khi chạy test.

Bật bằng `LLM_PROVIDER=mock` trong .env. Nhờ nó, frontend và toàn bộ luồng SSE
có thể phát triển/test mà không cần GPU (giảm rủi ro "free GPU không ổn định").
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

from app.modules.chat.schemas import ChatMessage
from app.modules.llm.providers.base import LLMChunk, LLMModel, LLMProvider, LLMResult

_CHUNK_DELAY_SECONDS = 0.04


class MockProvider(LLMProvider):
    """Trả lời bằng cách nhại lại tin nhắn cuối, phát từng từ một."""

    name = "mock"

    def __init__(
        self,
        model: str = "mock-model",
        chunk_delay: float = _CHUNK_DELAY_SECONDS,
    ) -> None:
        self._model = model
        self._chunk_delay = chunk_delay

    @property
    def default_model(self) -> str:
        return self._model

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[LLMModel]:
        return [
            LLMModel(
                id=self._model,
                name="Mock Model",
                description="Model giả lập, không cần GPU",
                size_bytes=None,
            )
        ]

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResult:
        text = _compose_answer(messages)
        return LLMResult(
            content=text,
            model=model or self._model,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(text.split()),
        )

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]:
        text = _compose_answer(messages)
        words = text.split(" ")

        for index, word in enumerate(words):
            piece = word if index == 0 else f" {word}"
            yield LLMChunk(content=piece)
            if self._chunk_delay:
                await asyncio.sleep(self._chunk_delay)

        yield LLMChunk(
            content="",
            done=True,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(words),
        )


def _compose_answer(messages: Sequence[ChatMessage]) -> str:
    """Sinh câu trả lời giả lập, đủ dài để nhìn rõ hiệu ứng streaming."""
    last_user = next(
        (m.content for m in reversed(messages) if m.role == "user"), "(không có nội dung)"
    )
    return (
        f'[MOCK] Tôi đã nhận được tin nhắn của bạn: "{last_user}". '
        "Đây là câu trả lời giả lập do backend đang chạy ở chế độ mock, "
        "chưa gọi tới model thật. Hãy cài Ollama và đặt LLM_PROVIDER=ollama "
        "trong file .env để chat với model mã nguồn mở."
    )
