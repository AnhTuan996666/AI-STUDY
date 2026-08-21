"""Schema request/response cho nhóm /conversations.

Khớp `conversationSchema.ts` phía frontend: cùng tên trường snake_case, cùng khuôn bọc
`{ conversation: ... }` / `{ conversations: [...] }`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.conversations.models import (
    TITLE_MAX_LENGTH,
    Conversation,
    Message,
)


class MessageDto(BaseModel):
    """Một tin nhắn trong hội thoại."""

    id: UUID
    role: str
    content: str
    created_at: datetime

    @classmethod
    def from_domain(cls, message: Message) -> MessageDto:
        return cls(
            id=message.id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
        )


class ConversationSummary(BaseModel):
    """Bản rút gọn cho sidebar — không kèm tin nhắn."""

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    message_count: int

    @classmethod
    def from_domain(cls, conversation: Conversation) -> ConversationSummary:
        return cls(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            is_pinned=conversation.is_pinned,
            message_count=conversation.message_count,
        )


class ConversationDetail(ConversationSummary):
    """Bản đầy đủ — kèm toàn bộ tin nhắn."""

    messages: list[MessageDto] = Field(default_factory=list)

    @classmethod
    def from_domain_with_messages(
        cls, conversation: Conversation, messages: list[Message]
    ) -> ConversationDetail:
        return cls(
            **ConversationSummary.from_domain(conversation).model_dump(),
            messages=[MessageDto.from_domain(m) for m in messages],
        )


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationResponse(BaseModel):
    conversation: ConversationDetail


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Hội thoại mới", min_length=1, max_length=TITLE_MAX_LENGTH)


class UpdateConversationRequest(BaseModel):
    """Gửi trường nào sửa trường đó; bỏ trống cả hai là không đổi gì."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    is_pinned: bool | None = None
