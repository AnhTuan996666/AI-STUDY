"""Nghiệp vụ cài đặt theo tài khoản (FR-08)."""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.modules.settings.models import UserSettings
from app.modules.settings.repository import SettingsRepository

logger = get_logger(__name__)


class SettingsService:
    """Đọc/ghi tuỳ chọn cá nhân."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def get(self, user_id: UUID) -> UserSettings:
        """Chưa từng lưu thì trả bản mặc định — GET /settings không bao giờ 404."""
        stored = await self._repository.get(user_id)
        return stored or UserSettings.defaults_for(user_id)

    async def save(self, settings: UserSettings) -> UserSettings:
        """Ghi đè toàn bộ cài đặt và trả về bản đã lưu (đã chuẩn hóa)."""
        saved = await self._repository.save(settings)
        logger.info("settings.saved user=%s theme=%s", saved.user_id, saved.theme)
        return saved
