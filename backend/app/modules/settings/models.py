"""Domain model + ORM model của cài đặt theo tài khoản.

Khớp `settingsSchema` phía frontend (`frontend/src/schemas/settingsSchema.ts`) và mục
"Settings" trong docs/API_CONTRACT.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcDateTime

DEFAULT_TEMPERATURE = 0.7
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


class Theme(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass
class UserSettings:
    """Tuỳ chọn cá nhân của một tài khoản."""

    user_id: UUID
    theme: Theme = Theme.SYSTEM
    model: str | None = None
    temperature: float = DEFAULT_TEMPERATURE
    send_on_enter: bool = True
    show_suggestions: bool = True

    @classmethod
    def defaults_for(cls, user_id: UUID) -> UserSettings:
        """Bản mặc định cho tài khoản chưa từng lưu cài đặt nào."""
        return cls(user_id=user_id)


class UserSettingsORM(Base):
    """Bảng `user_settings` — quan hệ 1-1 với `users`."""

    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    theme: Mapped[str] = mapped_column(String(16), default=Theme.SYSTEM.value)
    model: Mapped[str | None] = mapped_column(String(255), default=None)
    temperature: Mapped[float] = mapped_column(Float, default=DEFAULT_TEMPERATURE)
    send_on_enter: Mapped[bool] = mapped_column(Boolean, default=True)
    show_suggestions: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def to_domain(self) -> UserSettings:
        return UserSettings(
            user_id=self.user_id,
            theme=Theme(self.theme),
            model=self.model,
            temperature=self.temperature,
            send_on_enter=self.send_on_enter,
            show_suggestions=self.show_suggestions,
        )

    def apply(self, settings: UserSettings) -> None:
        """Ghi đè bằng giá trị mới (PUT /settings thay toàn bộ, không vá từng trường)."""
        self.theme = settings.theme.value
        self.model = settings.model
        self.temperature = settings.temperature
        self.send_on_enter = settings.send_on_enter
        self.show_suggestions = settings.show_suggestions

    @classmethod
    def from_domain(cls, settings: UserSettings) -> UserSettingsORM:
        row = cls(user_id=settings.user_id)
        row.apply(settings)
        return row
