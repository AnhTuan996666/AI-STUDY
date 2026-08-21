"""Test tầng repository (bản in-memory)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.conversations.models import Conversation, Message, MessageRole
from app.modules.conversations.repository import (
    InMemoryConversationRepository,
    InMemoryMessageRepository,
)

USER_A = uuid4()
USER_B = uuid4()


@pytest.fixture
def conversations() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


@pytest.fixture
def messages() -> InMemoryMessageRepository:
    return InMemoryMessageRepository()


async def test_create_then_get(conversations: InMemoryConversationRepository) -> None:
    created = await conversations.create(Conversation(user_id=USER_A, title="Chào"))

    found = await conversations.get(created.id)

    assert found is not None
    assert found.title == "Chào"


async def test_get_missing_returns_none(
    conversations: InMemoryConversationRepository,
) -> None:
    assert await conversations.get(uuid4()) is None


async def test_list_by_user_only_returns_owned(
    conversations: InMemoryConversationRepository,
) -> None:
    await conversations.create(Conversation(user_id=USER_A, title="của A"))
    await conversations.create(Conversation(user_id=USER_B, title="của B"))

    owned = await conversations.list_by_user(USER_A)

    assert [item.title for item in owned] == ["của A"]


async def test_list_by_user_sorts_recently_updated_first(
    conversations: InMemoryConversationRepository,
) -> None:
    first = await conversations.create(Conversation(user_id=USER_A, title="cũ"))
    await conversations.create(Conversation(user_id=USER_A, title="mới"))
    first.touch()  # chạm vào cái cũ -> phải nhảy lên đầu

    owned = await conversations.list_by_user(USER_A)

    assert [item.title for item in owned] == ["cũ", "mới"]


async def test_list_by_user_respects_limit(
    conversations: InMemoryConversationRepository,
) -> None:
    for index in range(5):
        await conversations.create(Conversation(user_id=USER_A, title=f"c{index}"))

    assert len(await conversations.list_by_user(USER_A, limit=3)) == 3


async def test_update_changes_title(
    conversations: InMemoryConversationRepository,
) -> None:
    created = await conversations.create(Conversation(user_id=USER_A))

    updated = await conversations.update(created.id, title="  Tên mới  ")

    assert updated is not None
    assert updated.title == "Tên mới"


async def test_update_toggles_pin(
    conversations: InMemoryConversationRepository,
) -> None:
    created = await conversations.create(Conversation(user_id=USER_A))

    updated = await conversations.update(created.id, is_pinned=True)

    assert updated is not None
    assert updated.is_pinned is True


async def test_update_ignores_blank_title(
    conversations: InMemoryConversationRepository,
) -> None:
    created = await conversations.create(Conversation(user_id=USER_A, title="Giữ nguyên"))

    updated = await conversations.update(created.id, title="   ")

    assert updated is not None
    assert updated.title == "Giữ nguyên"


async def test_update_missing_returns_none(
    conversations: InMemoryConversationRepository,
) -> None:
    assert await conversations.update(uuid4(), title="x") is None


async def test_delete_removes_conversation(
    conversations: InMemoryConversationRepository,
) -> None:
    created = await conversations.create(Conversation(user_id=USER_A))

    assert await conversations.delete(created.id) is True
    assert await conversations.delete(created.id) is False
    assert await conversations.get(created.id) is None


async def test_messages_kept_in_insert_order(
    messages: InMemoryMessageRepository,
) -> None:
    conversation_id = uuid4()
    for index in range(3):
        await messages.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=f"m{index}",
            )
        )

    history = await messages.list_by_conversation(conversation_id)

    assert [item.content for item in history] == ["m0", "m1", "m2"]


async def test_messages_limit_returns_most_recent_in_order(
    messages: InMemoryMessageRepository,
) -> None:
    conversation_id = uuid4()
    for index in range(5):
        await messages.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=f"m{index}",
            )
        )

    history = await messages.list_by_conversation(conversation_id, limit=2)

    assert [item.content for item in history] == ["m3", "m4"]


async def test_messages_isolated_per_conversation(
    messages: InMemoryMessageRepository,
) -> None:
    first, second = uuid4(), uuid4()
    await messages.add(Message(conversation_id=first, role=MessageRole.USER, content="của 1"))

    assert await messages.list_by_conversation(second) == []


async def test_delete_by_conversation_returns_count(
    messages: InMemoryMessageRepository,
) -> None:
    conversation_id = uuid4()
    for _ in range(3):
        await messages.add(
            Message(conversation_id=conversation_id, role=MessageRole.USER, content="x")
        )

    assert await messages.delete_by_conversation(conversation_id) == 3
    assert await messages.list_by_conversation(conversation_id) == []


def test_message_total_tokens() -> None:
    message = Message(
        conversation_id=uuid4(),
        role=MessageRole.ASSISTANT,
        content="hi",
        prompt_tokens=10,
        completion_tokens=5,
    )

    assert message.total_tokens == 15


def test_message_total_tokens_none_when_incomplete() -> None:
    message = Message(
        conversation_id=uuid4(), role=MessageRole.USER, content="hi", prompt_tokens=10
    )

    assert message.total_tokens is None
