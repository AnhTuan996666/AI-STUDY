"""Đọc/ghi cài đặt theo tài khoản.

Cấu trúc file giống `app/modules/auth/repository.py`: interface trước, rồi bản
PostgreSQL, rồi bản in-memory dùng khi chưa cấu hình DATABASE_NAME.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import UserSettings, UserSettingsORM


class SettingsRepository(ABC):
    """Cài đặt gắn theo tài khoản — phục vụ FR-08."""

    @abstractmethod
    async def get(self, user_id: UUID) -> UserSettings | None:
        """None nghĩa là user chưa từng lưu — tầng service sẽ trả bản mặc định."""

    @abstractmethod
    async def save(self, settings: UserSettings) -> UserSettings:
        """Tạo mới hoặc ghi đè toàn bộ cài đặt của user."""


class SqlSettingsRepository(SettingsRepository):
    """Bản chạy thật trên PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> UserSettings | None:
        row = await self._session.get(UserSettingsORM, user_id)
        return row.to_domain() if row else None

    async def save(self, settings: UserSettings) -> UserSettings:
        row = await self._session.get(UserSettingsORM, settings.user_id)
        if row is None:
            row = UserSettingsORM.from_domain(settings)
            self._session.add(row)
        else:
            row.apply(settings)

        await self._session.flush()
        return row.to_domain()


class InMemorySettingsRepository(SettingsRepository):
    """Lưu cài đặt trong dict theo user_id."""

    def __init__(self) -> None:
        self._items: dict[UUID, UserSettings] = {}

    async def get(self, user_id: UUID) -> UserSettings | None:
        return self._items.get(user_id)

    async def save(self, settings: UserSettings) -> UserSettings:
        # Copy để người gọi sửa dataclass của mình cũng không đụng vào bản đã lưu.
        stored = replace(settings)
        self._items[settings.user_id] = stored
        return stored

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()
