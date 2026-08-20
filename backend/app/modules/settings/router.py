"""Địa chỉ API của module settings.

    GET /settings   đọc cài đặt của tài khoản đang đăng nhập
    PUT /settings   ghi đè cài đặt

Cả hai đều cần token. Khuôn phản hồi: docs/API_CONTRACT.md mục "Settings".
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SettingsServiceDep
from app.modules.settings.schemas import (
    SettingsPayload,
    SettingsResponse,
    SettingsUpdateRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse, summary="Đọc cài đặt cá nhân")
async def read_settings(user: CurrentUserDep, service: SettingsServiceDep) -> SettingsResponse:
    """FR-08 — chưa từng lưu thì trả bản mặc định, không bao giờ 404."""
    settings = await service.get(user.id)
    return SettingsResponse(settings=SettingsPayload.from_domain(settings))


@router.put("", response_model=SettingsResponse, summary="Lưu cài đặt cá nhân")
async def update_settings(
    payload: SettingsUpdateRequest,
    user: CurrentUserDep,
    service: SettingsServiceDep,
) -> SettingsResponse:
    """Ghi đè toàn bộ và trả về bản đã lưu (đã chuẩn hóa)."""
    saved = await service.save(payload.settings.to_domain(user.id))
    return SettingsResponse(settings=SettingsPayload.from_domain(saved))
