"""Schema cho GET /models — danh sách model backend đang phục vụ."""

from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Một model có thể chọn. Chỉ `id` là bắt buộc — đúng hợp đồng với frontend."""

    id: str
    name: str | None = None
    description: str | None = None
    size_bytes: int | None = None
    is_default: bool = False


class ModelListResponse(BaseModel):
    """Khuôn bọc ngoài — frontend đọc `payload.models`."""

    models: list[ModelInfo]
