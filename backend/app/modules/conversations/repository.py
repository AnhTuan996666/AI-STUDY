"""Đọc/ghi lịch sử hội thoại.

Cấu trúc file giống `app/modules/auth/repository.py`: interface trước, rồi các bản cài
đặt. Hiện mới có bản in-memory — lịch sử chat vẫn nằm ở trình duyệt (FR-05 chưa làm).

Cảnh báo: bản in-memory mất dữ liệu khi restart và không chia sẻ giữa nhiều worker.
KHÔNG dùng ở production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from uuid import UUID

from app.modules.conversations.models import Conversation, Message


class ConversationRepository(ABC):
    """CRUD hội thoại — phục vụ FR-05, FR-06, FR-07."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Lưu hội thoại mới, trả về bản đã lưu."""

    @abstractmethod
    async def get(self, conversation_id: UUID) -> Conversation | None:
        """Lấy 1 hội thoại theo id; None nếu không tồn tại."""

    @abstractmethod
    async def list_by_user(self, user_id: UUID, limit: int = 50) -> list[Conversation]:
        """Danh sách hội thoại của user, mới cập nhật nhất lên đầu (FR-06)."""

    @abstractmethod
    async def rename(self, conversation_id: UUID, title: str) -> Conversation | None:
        """Đổi tên; None nếu không tìm thấy (FR-07)."""

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> bool:
        """Xóa hội thoại và toàn bộ tin nhắn của nó. True nếu có xóa (FR-07)."""


class MessageRepository(ABC):
    """CRUD tin nhắn — phục vụ FR-05."""

    @abstractmethod
    async def add(self, message: Message) -> Message:
        """Thêm 1 tin nhắn vào hội thoại."""

    @abstractmethod
    async def list_by_conversation(self, conversation_id: UUID, limit: int = 200) -> list[Message]:
        """Lịch sử 1 hội thoại theo đúng thứ tự thời gian."""

    @abstractmethod
    async def delete_by_conversation(self, conversation_id: UUID) -> int:
        """Xóa toàn bộ tin nhắn của hội thoại, trả về số bản ghi đã xóa."""


# ========================= bản in-memory ================================


class InMemoryConversationRepository(ConversationRepository):
    """Lưu hội thoại trong dict theo id."""

    def __init__(self) -> None:
        self._items: dict[UUID, Conversation] = {}

    async def create(self, conversation: Conversation) -> Conversation:
        self._items[conversation.id] = conversation
        return conversation

    async def get(self, conversation_id: UUID) -> Conversation | None:
        return self._items.get(conversation_id)

    async def list_by_user(self, user_id: UUID, limit: int = 50) -> list[Conversation]:
        owned = [item for item in self._items.values() if item.user_id == user_id]
        owned.sort(key=lambda item: item.updated_at, reverse=True)
        return owned[:limit]

    async def rename(self, conversation_id: UUID, title: str) -> Conversation | None:
        conversation = self._items.get(conversation_id)
        if conversation is None:
            return None

        conversation.rename(title)
        return conversation

    async def delete(self, conversation_id: UUID) -> bool:
        # Với DB thật, tin nhắn tự xóa theo `on delete cascade`. Bản in-memory
        # không có ràng buộc đó nên service phải gọi thêm MessageRepository.
        return self._items.pop(conversation_id, None) is not None

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

    async def list_by_conversation(self, conversation_id: UUID, limit: int = 200) -> list[Message]:
        history = self._items.get(conversation_id, [])
        # Lấy `limit` tin GẦN NHẤT nhưng vẫn trả theo thứ tự thời gian tăng dần,
        # đúng như truy vấn SQL tương ứng trong docs/DATABASE_SCHEMA.md.
        return history[-limit:]

    async def delete_by_conversation(self, conversation_id: UUID) -> int:
        removed = self._items.pop(conversation_id, [])
        return len(removed)

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()
