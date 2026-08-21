"""Endpoint chat: bản thường (JSON) và bản streaming (SSE)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import ChatHistoryWriterDep, ChatServiceDep, OptionalUserDep
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.modules.chat.schemas import ChatRequest, ChatResponse, StreamEvent
from app.modules.chat.service import ChatService
from app.modules.conversations.history_writer import ChatHistoryWriter
from app.modules.conversations.router import ConversationNotFoundError

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Header cần thiết để proxy (nginx/Render) không gom buffer làm mất hiệu ứng streaming.
_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat (chờ trả lời đầy đủ)",
)
async def chat(payload: ChatRequest, service: ChatServiceDep) -> ChatResponse:
    """FR-03 — gửi tin nhắn, nhận toàn bộ câu trả lời trong 1 response."""
    return await service.complete(
        payload.messages,
        model=payload.model,
        temperature=payload.temperature,
    )


@router.post(
    "/stream",
    summary="Chat (streaming qua SSE)",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    service: ChatServiceDep,
    user: OptionalUserDep,
    history: ChatHistoryWriterDep,
) -> StreamingResponse:
    """FR-04 — trả lời dần theo thời gian thực.

    Định dạng mỗi sự kiện: `data: {json}\\n\\n`
    - `{"type":"queued","position":...}`  (khi phải xếp hàng)
    - `{"type":"delta","content":"..."}`
    - `{"type":"done","model":...,"latency_ms":...,"usage":{...}}`
    - `{"type":"error","message":"..."}`

    Nếu có `conversation_id` và đã đăng nhập: lưu tin của user NGAY (trước khi stream)
    và lưu câu trả lời khi stream xong — kể cả khi người dùng bấm Dừng giữa chừng.
    """
    persist = payload.conversation_id is not None and user is not None
    if persist:
        # Lưu tin user trước, đồng thời là chỗ kiểm sở hữu: không thuộc user -> 404 thật
        # (chưa gửi byte stream nào nên trả status code chuẩn được).
        saved = await history.save_user_message(
            user.id, payload.conversation_id, _latest_user_content(payload)
        )
        if not saved:
            raise ConversationNotFoundError("Không tìm thấy hội thoại.")

    return StreamingResponse(
        _event_stream(service, payload, request, history if persist else None),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _event_stream(
    service: ChatService,
    payload: ChatRequest,
    request: Request,
    history: ChatHistoryWriter | None,
) -> AsyncIterator[str]:
    """Sinh chuỗi SSE, luôn đóng luồng bằng 1 event `done` hoặc `error`.

    Gom câu trả lời vào `answer` và ghi ở `finally` — vào đó cả khi client ngắt kết nối
    (contract: bấm Dừng vẫn lưu phần đã sinh).
    """
    answer: list[str] = []
    try:
        async for event in service.stream(
            payload.messages,
            model=payload.model,
            temperature=payload.temperature,
        ):
            if await request.is_disconnected():
                logger.info("Client ngắt kết nối, dừng stream.")
                return
            if event.type == "delta" and event.content:
                answer.append(event.content)
            yield _sse(event)

    except asyncio.CancelledError:
        logger.info("Stream bị hủy.")
        raise

    except AppError as exc:
        logger.warning("Lỗi khi streaming [%s]: %s", exc.code, exc.message)
        yield _sse(StreamEvent(type="error", message=exc.message))

    except Exception:  # noqa: BLE001 - lỗi ngoài dự kiến vẫn phải báo cho client
        logger.exception("Lỗi không mong đợi khi streaming")
        yield _sse(StreamEvent(type="error", message="Đã có lỗi xảy ra phía máy chủ."))

    finally:
        if history is not None and payload.conversation_id is not None:
            await history.save_assistant_message(payload.conversation_id, "".join(answer))


def _latest_user_content(payload: ChatRequest) -> str:
    """Lấy nội dung tin mới nhất của user để lưu (frontend gửi kèm cả lịch sử)."""
    for message in reversed(payload.messages):
        if message.role == "user":
            return message.content
    return ""


def _sse(event: StreamEvent) -> str:
    """Đóng gói 1 StreamEvent thành khung SSE."""
    return f"data: {event.model_dump_json(exclude_none=True)}\n\n"
