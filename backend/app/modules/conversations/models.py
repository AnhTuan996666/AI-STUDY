"""Dữ liệu của module conversations: hội thoại và tin nhắn.

Mỗi bảng có domain model (dataclass, tầng service dùng) + ORM model (bảng thật), nối
bằng `to_domain()` / `from_domain()` — cùng khuôn với `app/modules/auth/models.py`.

DDL tham chiếu: docs/DATABASE_SCHEMA.md mục 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcDateTime

DEFAULT_TITLE = "Hội thoại mới"
TITLE_MAX_LENGTH = 40


class MessageRole(StrEnum):
    """Khớp với enum `message_role` trong PostgreSQL."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# ============================ conversations =============================


@dataclass
class Conversation:
    """Một cuộc trò chuyện thuộc về một user.

    `message_count` không phải cột trong bảng `conversations` — nó do repository đếm từ
    bảng `messages` rồi gắn vào khi trả về, để sidebar biết số tin mà chưa cần tải nội dung.
    """

    user_id: UUID
    title: str = DEFAULT_TITLE
    model: str | None = None
    is_pinned: bool = False
    message_count: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Đánh dấu vừa có hoạt động — dùng để sắp xếp sidebar (FR-06)."""
        self.updated_at = datetime.now(UTC)

    def rename(self, title: str) -> None:
        """Đổi tên hội thoại (FR-07). Tên rỗng thì giữ nguyên tên cũ."""
        clean = title.strip()
        if not clean:
            return
        self.title = clean
        self.touch()


class ConversationORM(Base):
    """Bảng `conversations`."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), default=DEFAULT_TITLE)
    model: Mapped[str | None] = mapped_column(String(255), default=None)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def to_domain(self, message_count: int = 0) -> Conversation:
        return Conversation(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            model=self.model,
            is_pinned=self.is_pinned,
            message_count=message_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, conversation: Conversation) -> ConversationORM:
        return cls(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            model=conversation.model,
            is_pinned=conversation.is_pinned,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


# ============================== messages ================================


@dataclass
class Message:
    """Một tin nhắn trong hội thoại.

    Các trường token/latency chỉ có ở tin của assistant; tin của user để None.
    """

    conversation_id: UUID
    role: MessageRole
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None or self.completion_tokens is None:
            return None
        return self.prompt_tokens + self.completion_tokens


class MessageORM(Base):
    """Bảng `messages`."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(default=None)
    completion_tokens: Mapped[int | None] = mapped_column(default=None)
    latency_ms: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))

    def to_domain(self) -> Message:
        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            role=MessageRole(self.role),
            content=self.content,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, message: Message) -> MessageORM:
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )
