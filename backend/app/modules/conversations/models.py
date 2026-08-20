"""Dữ liệu của module conversations: hội thoại và tin nhắn trong hội thoại.

Hiện mới có **domain model** (dataclass). Khi cắm lịch sử chat vào PostgreSQL (FR-05),
thêm `ConversationORM` / `MessageORM` ngay trong file này theo đúng khuôn của
`app/modules/auth/models.py`, rồi khai báo bản `Sql...Repository` ở `repository.py`.

DDL tham chiếu: docs/DATABASE_SCHEMA.md mục 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

DEFAULT_TITLE = "Hội thoại mới"
TITLE_MAX_LENGTH = 40


@dataclass
class Conversation:
    """Một cuộc trò chuyện thuộc về một user."""

    user_id: UUID
    title: str = DEFAULT_TITLE
    model: str | None = None
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


class MessageRole(StrEnum):
    """Khớp với enum `message_role` trong PostgreSQL."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


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
