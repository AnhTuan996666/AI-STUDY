"""Nghiệp vụ hội thoại: CRUD + lưu tin nhắn của một lượt chat (FR-05, FR-06, FR-07).

Quy tắc sở hữu nằm trọn ở đây: mọi thao tác đều nhận `user_id` và chỉ đụng tới hội thoại
của đúng người đó. Hội thoại của người khác coi như **không tồn tại** (trả None → router
đáp 404), không bao giờ lộ ra là id đó có thật.
"""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.modules.conversations.models import Conversation, Message, MessageRole
from app.modules.conversations.repository import (
    ConversationRepository,
    MessageRepository,
)

logger = get_logger(__name__)


class ConversationService:
    """Điều phối hội thoại và tin nhắn của một user."""

    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
    ) -> None:
        self._conversations = conversations
        self._messages = messages

    # --- CRUD -------------------------------------------------------------

    async def list_for(self, user_id: UUID) -> list[Conversation]:
        return await self._conversations.list_by_user(user_id)

    async def create(self, user_id: UUID, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title.strip() or "Hội thoại mới")
        created = await self._conversations.create(conversation)
        logger.info("conversation.create user=%s id=%s", user_id, created.id)
        return created

    async def get_owned(self, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        """Hội thoại nếu thuộc về user; None nếu không tồn tại HOẶC của người khác."""
        conversation = await self._conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return conversation

    async def get_with_messages(
        self, user_id: UUID, conversation_id: UUID
    ) -> tuple[Conversation, list[Message]] | None:
        conversation = await self.get_owned(user_id, conversation_id)
        if conversation is None:
            return None
        messages = await self._messages.list_by_conversation(conversation_id)
        return conversation, messages

    async def update(
        self,
        user_id: UUID,
        conversation_id: UUID,
        *,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> Conversation | None:
        if await self.get_owned(user_id, conversation_id) is None:
            return None
        return await self._conversations.update(conversation_id, title=title, is_pinned=is_pinned)

    async def delete(self, user_id: UUID, conversation_id: UUID) -> bool:
        if await self.get_owned(user_id, conversation_id) is None:
            return False
        return await self._conversations.delete(conversation_id)

    # --- lưu tin của một lượt chat (dùng từ /chat/stream) -----------------

    async def save_user_message(self, user_id: UUID, conversation_id: UUID, content: str) -> bool:
        """Lưu tin của user ngay khi nhận. False nếu hội thoại không thuộc user."""
        if await self.get_owned(user_id, conversation_id) is None:
            return False
        await self._messages.add(
            Message(conversation_id=conversation_id, role=MessageRole.USER, content=content)
        )
        await self._conversations.touch(conversation_id)
        return True

    async def save_assistant_message(
        self,
        conversation_id: UUID,
        content: str,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """Lưu câu trả lời khi stream xong (hoặc phần đã sinh khi người dùng bấm Dừng).

        Ownership đã kiểm ở `save_user_message` trước đó nên ở đây không kiểm lại; nội
        dung rỗng thì bỏ qua (chưa kịp sinh chữ nào).
        """
        if not content.strip():
            return
        await self._messages.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
        )
        await self._conversations.touch(conversation_id)
