"""Đọc/ghi hội thoại và tin nhắn.

Cấu trúc file giống `app/modules/auth/repository.py`: interface trước, rồi bản
PostgreSQL, rồi bản in-memory (dùng khi chưa cấu hình DATABASE_NAME, cho dev/test).

`message_count` trên `Conversation` do repository đếm và gắn vào lúc trả về — không phải
cột trong bảng.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.models import (
    Conversation,
    ConversationORM,
    Message,
    MessageORM,
)


class ConversationRepository(ABC):
    """CRUD hội thoại — phục vụ FR-05, FR-06, FR-07."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Lưu hội thoại mới, trả về bản đã lưu (message_count = 0)."""

    @abstractmethod
    async def get(self, conversation_id: UUID) -> Conversation | None:
        """Lấy 1 hội thoại (kèm message_count); None nếu không tồn tại."""

    @abstractmethod
    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[Conversation]:
        """Danh sách hội thoại của user, mới cập nhật nhất lên đầu (FR-06)."""

    @abstractmethod
    async def update(
        self,
        conversation_id: UUID,
        *,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> Conversation | None:
        """Sửa tên và/hoặc trạng thái ghim; trường None nghĩa là không đổi (FR-07)."""

    @abstractmethod
    async def touch(self, conversation_id: UUID) -> None:
        """Cập nhật `updated_at` để hội thoại vừa nhắn nhảy lên đầu sidebar."""

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> bool:
        """Xóa hội thoại và toàn bộ tin nhắn của nó. True nếu có xóa (FR-07)."""


class MessageRepository(ABC):
    """CRUD tin nhắn — phục vụ FR-05."""

    @abstractmethod
    async def add(self, message: Message) -> Message:
        """Thêm 1 tin nhắn vào hội thoại."""

    @abstractmethod
    async def list_by_conversation(self, conversation_id: UUID, limit: int = 500) -> list[Message]:
        """Lịch sử 1 hội thoại theo đúng thứ tự thời gian."""

    @abstractmethod
    async def delete_by_conversation(self, conversation_id: UUID) -> int:
        """Xóa toàn bộ tin nhắn của hội thoại, trả về số bản ghi đã xóa."""


# ========================= bản PostgreSQL ===============================


class SqlConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        row = ConversationORM.from_domain(conversation)
        self._session.add(row)
        await self._session.flush()
        return row.to_domain(message_count=0)

    async def get(self, conversation_id: UUID) -> Conversation | None:
        row = await self._session.get(ConversationORM, conversation_id)
        if row is None:
            return None
        return row.to_domain(message_count=await self._count(conversation_id))

    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[Conversation]:
        # Đếm tin nhắn bằng một truy vấn có LEFT JOIN + GROUP BY, tránh N+1.
        count = func.count(MessageORM.id)
        stmt = (
            select(ConversationORM, count)
            .outerjoin(MessageORM, MessageORM.conversation_id == ConversationORM.id)
            .where(ConversationORM.user_id == user_id)
            .group_by(ConversationORM.id)
            .order_by(ConversationORM.updated_at.desc())
            .limit(limit)
        )
        rows = await self._session.execute(stmt)
        return [row.to_domain(message_count=n) for row, n in rows.all()]

    async def update(
        self,
        conversation_id: UUID,
        *,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> Conversation | None:
        row = await self._session.get(ConversationORM, conversation_id)
        if row is None:
            return None

        if title is not None:
            clean = title.strip()
            if clean:
                row.title = clean
        if is_pinned is not None:
            row.is_pinned = is_pinned

        await self._session.flush()
        return row.to_domain(message_count=await self._count(conversation_id))

    async def touch(self, conversation_id: UUID) -> None:
        row = await self._session.get(ConversationORM, conversation_id)
        if row is not None:
            row.updated_at = datetime.now(UTC)
            await self._session.flush()

    async def delete(self, conversation_id: UUID) -> bool:
        # Tin nhắn tự xóa theo `ON DELETE CASCADE`.
        row = await self._session.get(ConversationORM, conversation_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def _count(self, conversation_id: UUID) -> int:
        stmt = select(func.count(MessageORM.id)).where(
            MessageORM.conversation_id == conversation_id
        )
        return (await self._session.execute(stmt)).scalar_one()


class SqlMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> Message:
        row = MessageORM.from_domain(message)
        self._session.add(row)
        await self._session.flush()
        return row.to_domain()

    async def list_by_conversation(self, conversation_id: UUID, limit: int = 500) -> list[Message]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            .order_by(MessageORM.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [row.to_domain() for row in rows]

    async def delete_by_conversation(self, conversation_id: UUID) -> int:
        stmt = delete(MessageORM).where(MessageORM.conversation_id == conversation_id)
        result = await self._session.execute(stmt)
        return result.rowcount or 0


# ========================= bản in-memory ================================


class InMemoryConversationRepository(ConversationRepository):
    """Lưu hội thoại trong dict theo id. message_count đọc từ message repo nếu có gắn."""

    def __init__(self, messages: InMemoryMessageRepository | None = None) -> None:
        self._items: dict[UUID, Conversation] = {}
        self._messages = messages

    def _with_count(self, conversation: Conversation) -> Conversation:
        if self._messages is not None:
            conversation.message_count = self._messages.count(conversation.id)
        return conversation

    async def create(self, conversation: Conversation) -> Conversation:
        self._items[conversation.id] = conversation
        return conversation

    async def get(self, conversation_id: UUID) -> Conversation | None:
        conversation = self._items.get(conversation_id)
        return self._with_count(conversation) if conversation else None

    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[Conversation]:
        owned = [item for item in self._items.values() if item.user_id == user_id]
        owned.sort(key=lambda item: item.updated_at, reverse=True)
        return [self._with_count(item) for item in owned[:limit]]

    async def update(
        self,
        conversation_id: UUID,
        *,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> Conversation | None:
        conversation = self._items.get(conversation_id)
        if conversation is None:
            return None

        if title is not None:
            conversation.rename(title)
        if is_pinned is not None:
            conversation.is_pinned = is_pinned

        return self._with_count(conversation)

    async def touch(self, conversation_id: UUID) -> None:
        conversation = self._items.get(conversation_id)
        if conversation is not None:
            conversation.touch()

    async def delete(self, conversation_id: UUID) -> bool:
        removed = self._items.pop(conversation_id, None) is not None
        if removed and self._messages is not None:
            await self._messages.delete_by_conversation(conversation_id)
        return removed

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()


class InMemoryMessageRepository(MessageRepository):
    """Lưu tin nhắn theo từng conversation_id, giữ đúng thứ tự thêm vào."""

    def __init__(self) -> None:
        self._items: dict[UUID, list[Message]] = defaultdict(list)

    async def add(self, message: Message) -> Message:
        self._items[message.conversation_id].append(message)
        return message

    async def list_by_conversation(self, conversation_id: UUID, limit: int = 500) -> list[Message]:
        history = self._items.get(conversation_id, [])
        return history[-limit:]

    def count(self, conversation_id: UUID) -> int:
        return len(self._items.get(conversation_id, []))

    async def delete_by_conversation(self, conversation_id: UUID) -> int:
        removed = self._items.pop(conversation_id, [])
        return len(removed)

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()
