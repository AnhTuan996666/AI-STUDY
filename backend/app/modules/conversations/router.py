"""Địa chỉ API của module conversations (FR-05, FR-06, FR-07).

    GET    /conversations        danh sách rút gọn cho sidebar
    POST   /conversations        tạo hội thoại rỗng (lấy id trước khi gửi tin đầu)
    GET    /conversations/{id}    bản đầy đủ kèm tin nhắn
    PATCH  /conversations/{id}    đổi tên / ghim
    DELETE /conversations/{id}    xoá

Tất cả cần token và chỉ đụng hội thoại của user đang đăng nhập. Không phải của mình thì
trả 404 (không dùng 403 — đừng để lộ id đó có tồn tại).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import ConversationServiceDep, CurrentUserDep
from app.core.exceptions import AppError
from app.modules.conversations.schemas import (
    ConversationDetail,
    ConversationListResponse,
    ConversationResponse,
    ConversationSummary,
    CreateConversationRequest,
    UpdateConversationRequest,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationNotFoundError(AppError):
    """Hội thoại không tồn tại hoặc không thuộc user đang đăng nhập."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "conversation_not_found"


@router.get("", response_model=ConversationListResponse, summary="Danh sách hội thoại")
async def list_conversations(
    user: CurrentUserDep, service: ConversationServiceDep
) -> ConversationListResponse:
    conversations = await service.list_for(user.id)
    return ConversationListResponse(
        conversations=[ConversationSummary.from_domain(c) for c in conversations]
    )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo hội thoại",
)
async def create_conversation(
    payload: CreateConversationRequest,
    user: CurrentUserDep,
    service: ConversationServiceDep,
) -> ConversationResponse:
    conversation = await service.create(user.id, payload.title)
    return ConversationResponse(
        conversation=ConversationDetail.from_domain_with_messages(conversation, [])
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Chi tiết hội thoại kèm tin nhắn",
)
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUserDep,
    service: ConversationServiceDep,
) -> ConversationResponse:
    result = await service.get_with_messages(user.id, conversation_id)
    if result is None:
        raise ConversationNotFoundError("Không tìm thấy hội thoại.")

    conversation, messages = result
    return ConversationResponse(
        conversation=ConversationDetail.from_domain_with_messages(conversation, messages)
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Đổi tên / ghim hội thoại",
)
async def update_conversation(
    conversation_id: UUID,
    payload: UpdateConversationRequest,
    user: CurrentUserDep,
    service: ConversationServiceDep,
) -> ConversationResponse:
    updated = await service.update(
        user.id, conversation_id, title=payload.title, is_pinned=payload.is_pinned
    )
    if updated is None:
        raise ConversationNotFoundError("Không tìm thấy hội thoại.")

    # Trả kèm tin nhắn để frontend giữ nguyên nội dung đang mở.
    result = await service.get_with_messages(user.id, conversation_id)
    conversation, messages = result if result else (updated, [])
    return ConversationResponse(
        conversation=ConversationDetail.from_domain_with_messages(conversation, messages)
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá hội thoại",
)
async def delete_conversation(
    conversation_id: UUID,
    user: CurrentUserDep,
    service: ConversationServiceDep,
) -> None:
    if not await service.delete(user.id, conversation_id):
        raise ConversationNotFoundError("Không tìm thấy hội thoại.")
