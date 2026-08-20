"""Địa chỉ API của module llm.

    GET /models   danh sách model đang phục vụ

Không cần đăng nhập: menu chọn model ở header phải dùng được ngay từ lúc chưa đăng nhập.
Khuôn phản hồi: docs/API_CONTRACT.md mục "Models".
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ModelServiceDep
from app.modules.llm.schemas import ModelListResponse

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelListResponse, summary="Danh sách model")
async def list_models(service: ModelServiceDep) -> ModelListResponse:
    """Đọc từ model server đang chạy (Ollama `GET /api/tags`).

    Model server chết thì vẫn trả về ít nhất model mặc định, để người dùng không rơi
    vào menu rỗng không chọn được gì.
    """
    return ModelListResponse(models=await service.list_models())
