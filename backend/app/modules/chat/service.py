"""Nghiệp vụ chat: dựng ngữ cảnh, gọi provider, đóng gói kết quả.

Tầng này KHÔNG biết gì về HTTP/SSE — chỉ trả dữ liệu thuần. Nhờ vậy sau này
thêm lưu DB (FR-05) chỉ cần sửa ở đây.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Sequence

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.chat.schemas import ChatMessage, ChatResponse, ChatUsage, StreamEvent
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.queue.base import RequestQueue

logger = get_logger(__name__)


class ChatService:
    """Điều phối một lượt chat.

    Mọi lượt gọi model đều đi qua `queue` để số lượt chạy đồng thời không vượt quá
    sức của GPU. Người thứ N+1 được xếp hàng và *biết mình đang chờ*, thay vì ngồi
    nhìn màn hình đứng im cho tới lúc timeout.
    """

    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings,
        queue: RequestQueue,
        client_key: str = "anonymous",
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._queue = queue
        self._client_key = client_key

    # --- public ----------------------------------------------------------

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Trả lời đầy đủ, không streaming (FR-03)."""
        prepared = self._prepare(messages)
        started = time.perf_counter()

        # Không có kênh nào báo vị trí trong bản non-streaming -> chỉ chờ tới lượt.
        async with self._queue.slot(self._client_key) as ticket:
            queued_ms = ticket.waited_ms
            result = await self._provider.generate(prepared, model=model, temperature=temperature)

        latency_ms = _elapsed_ms(started)
        logger.info(
            "chat.complete provider=%s model=%s queued=%dms latency=%dms chars=%d",
            self._provider.name,
            result.model,
            queued_ms,
            latency_ms,
            len(result.content),
        )

        return ChatResponse(
            content=result.content,
            model=result.model,
            latency_ms=latency_ms,
            usage=_usage(result.prompt_tokens, result.completion_tokens),
        )

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamEvent]:
        """Trả lời theo luồng, yield StreamEvent (FR-04).

        Luôn kết thúc bằng đúng 1 event `done` hoặc `error` để frontend biết dừng.
        """
        prepared = self._prepare(messages)
        model_name = model or self._provider.default_model
        prompt_tokens: int | None = None
        completion_tokens: int | None = None
        first_token_ms: int | None = None
        total_chars = 0

        # Giữ chỗ trước; `enqueue` raise QueueFullError ngay nếu hệ thống đã kín.
        ticket = await self._queue.enqueue(self._client_key)
        try:
            # Trong lúc chờ, báo vị trí về frontend để người dùng biết mình đang xếp hàng.
            async for position in ticket.wait_for_turn():
                stats = self._queue.stats()
                yield StreamEvent(
                    type="queued",
                    position=position,
                    queue_size=stats.waiting,
                    eta_seconds=stats.eta_seconds(position),
                )

            queued_ms = ticket.waited_ms
            started = time.perf_counter()

            async for chunk in self._provider.stream(
                prepared, model=model, temperature=temperature
            ):
                if chunk.prompt_tokens is not None:
                    prompt_tokens = chunk.prompt_tokens
                if chunk.completion_tokens is not None:
                    completion_tokens = chunk.completion_tokens

                if chunk.content:
                    if first_token_ms is None:
                        first_token_ms = _elapsed_ms(started)
                    total_chars += len(chunk.content)
                    yield StreamEvent(type="delta", content=chunk.content)
        finally:
            # Bắt buộc: client ngắt kết nối giữa chừng cũng phải trả slot, nếu không
            # hàng đợi sẽ tắc dần rồi đứng hẳn.
            await ticket.release()

        latency_ms = _elapsed_ms(started)
        logger.info(
            "chat.stream provider=%s model=%s queued=%dms ttft=%sms total=%dms chars=%d",
            self._provider.name,
            model_name,
            queued_ms,
            first_token_ms,
            latency_ms,
            total_chars,
        )

        yield StreamEvent(
            type="done",
            model=model_name,
            latency_ms=latency_ms,
            usage=_usage(prompt_tokens, completion_tokens),
        )

    # --- internals -------------------------------------------------------

    def _prepare(self, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        """Cắt bớt lịch sử và đảm bảo có đúng 1 system prompt ở đầu."""
        conversation = [m for m in messages if m.role != "system"]
        trimmed = conversation[-self._settings.max_history_messages :]
        system = ChatMessage(role="system", content=self._settings.system_prompt)
        return [system, *trimmed]


def _usage(prompt_tokens: int | None, completion_tokens: int | None) -> ChatUsage:
    total = (
        prompt_tokens + completion_tokens
        if prompt_tokens is not None and completion_tokens is not None
        else None
    )
    return ChatUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
    )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
