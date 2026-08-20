"""Endpoint chat: bản thường (JSON) và bản streaming (SSE)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import ChatServiceDep
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.modules.chat.schemas import ChatRequest, ChatResponse, StreamEvent
from app.modules.chat.service import ChatService

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
) -> StreamingResponse:
    """FR-04 — trả lời dần theo thời gian thực.

    Định dạng mỗi sự kiện: `data: {json}\\n\\n`
    - `{"type":"delta","content":"..."}`
    - `{"type":"done","model":...,"latency_ms":...,"usage":{...}}`
    - `{"type":"error","message":"..."}`
    """
    return StreamingResponse(
        _event_stream(service, payload, request),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _event_stream(
    service: ChatService,
    payload: ChatRequest,
    request: Request,
) -> AsyncIterator[str]:
    """Sinh chuỗi SSE, luôn đóng luồng bằng 1 event `done` hoặc `error`."""
    try:
        async for event in service.stream(
            payload.messages,
            model=payload.model,
            temperature=payload.temperature,
        ):
            if await request.is_disconnected():
                logger.info("Client ngắt kết nối, dừng stream.")
                return
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


def _sse(event: StreamEvent) -> str:
    """Đóng gói 1 StreamEvent thành khung SSE."""
    return f"data: {event.model_dump_json(exclude_none=True)}\n\n"
