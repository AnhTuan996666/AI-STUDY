"""Schema request/response cho API chat."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """Một tin nhắn trong hội thoại."""

    role: Role
    content: str = Field(min_length=1, max_length=32_000)


class ChatRequest(BaseModel):
    """Body của POST /chat và /chat/stream."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=200)
    model: str | None = Field(default=None, description="Ghi đè model mặc định")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    conversation_id: UUID | None = Field(
        default=None,
        description="Có id + đã đăng nhập -> backend tự lưu tin nhắn vào hội thoại này",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [{"role": "user", "content": "Xin chào, bạn là ai?"}],
                    "temperature": 0.7,
                }
            ]
        }
    }


class ChatUsage(BaseModel):
    """Thống kê token của một lượt gọi."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(BaseModel):
    """Kết quả POST /chat (không streaming)."""

    content: str
    model: str
    latency_ms: int
    usage: ChatUsage = Field(default_factory=ChatUsage)


class StreamEvent(BaseModel):
    """Một sự kiện SSE gửi cho frontend.

    type = "queued" -> có `position`, `queue_size`, `eta_seconds` (có thể lặp lại)
    type = "delta"  -> có `content`
    type = "done"   -> có `model`, `latency_ms`, `usage`
    type = "error"  -> có `message`

    Thứ tự đảm bảo: 0..n sự kiện `queued` (khi phải xếp hàng), rồi 0..n `delta`,
    và luôn kết thúc bằng đúng một `done` hoặc một `error`.
    """

    type: Literal["queued", "delta", "done", "error"]
    content: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    usage: ChatUsage | None = None
    message: str | None = None

    # --- chỉ có ở sự kiện "queued" ---
    position: int | None = Field(default=None, description="Vị trí trong hàng đợi, 1 = kế tiếp")
    queue_size: int | None = Field(default=None, description="Tổng số người đang chờ")
    eta_seconds: int | None = Field(default=None, description="Ước lượng thời gian chờ")
