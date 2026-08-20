"""Schema cho endpoint health."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class QueueStatus(BaseModel):
    """Tình trạng hàng đợi trước model server — dùng để theo dõi tải."""

    running: int
    waiting: int
    max_concurrent: int
    max_queue: int
    average_duration_ms: int | None = None


class HealthResponse(BaseModel):
    """Kết quả GET /health."""

    status: Literal["ok", "degraded"]
    app_version: str
    llm_provider: str
    llm_reachable: bool
    model: str
    queue: QueueStatus


class RootResponse(BaseModel):
    """Kết quả GET / — metadata cơ bản của app."""

    name: str
    version: str
    docs: str
    health: str
