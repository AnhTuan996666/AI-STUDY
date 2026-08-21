"""Ghi lịch sử chat cho luồng streaming, mỗi lần ghi là một transaction riêng.

Vì sao không dùng session theo request như các endpoint khác: câu trả lời được ghi ở
**cuối** stream (trong `finally`), và nếu client ngắt kết nối giữa chừng thì session
theo request sẽ bị rollback — mất phần đã sinh. Hợp đồng lại yêu cầu "bấm Dừng vẫn lưu
phần đã sinh được" (docs/API_CONTRACT.md). Nên ở đây mỗi lần ghi mở session riêng và
commit ngay.

Không có DB (`Database is None`) thì ghi thẳng vào repository in-memory dùng chung.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from app.db.session import Database
from app.modules.conversations.repository import (
    SqlConversationRepository,
    SqlMessageRepository,
)
from app.modules.conversations.service import ConversationService


class ChatHistoryWriter:
    """Lưu tin của user và câu trả lời của assistant, mỗi lần một transaction."""

    def __init__(self, database: Database | None, fallback: ConversationService) -> None:
        self._database = database
        self._fallback = fallback

    @asynccontextmanager
    async def _unit(self) -> AsyncIterator[ConversationService]:
        if self._database is None:
            yield self._fallback
            return

        async with self._database.session_factory() as session:
            service = ConversationService(
                SqlConversationRepository(session),
                SqlMessageRepository(session),
            )
            try:
                yield service
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def save_user_message(self, user_id: UUID, conversation_id: UUID, content: str) -> bool:
        """Lưu tin của user. False nếu hội thoại không thuộc user (router sẽ báo 404)."""
        async with self._unit() as service:
            return await service.save_user_message(user_id, conversation_id, content)

    async def save_assistant_message(
        self,
        conversation_id: UUID,
        content: str,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        async with self._unit() as service:
            await service.save_assistant_message(
                conversation_id,
                content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
