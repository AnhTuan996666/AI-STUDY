"""Schema request/response cho GET/PUT /settings.

Khớp `settingsSchema` phía frontend: cùng tên trường, cùng miền giá trị, cùng mặc định.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.settings.models import (
    DEFAULT_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    Theme,
    UserSettings,
)


class SettingsPayload(BaseModel):
    """Nội dung cài đặt. Mọi trường đều có mặc định để client gửi thiếu vẫn chạy."""

    theme: Literal["system", "light", "dark"] = "system"
    model: str | None = None
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    send_on_enter: bool = True
    show_suggestions: bool = True

    @classmethod
    def from_domain(cls, settings: UserSettings) -> SettingsPayload:
        return cls(
            theme=settings.theme.value,  # type: ignore[arg-type]
            model=settings.model,
            temperature=settings.temperature,
            send_on_enter=settings.send_on_enter,
            show_suggestions=settings.show_suggestions,
        )

    def to_domain(self, user_id: UUID) -> UserSettings:
        return UserSettings(
            user_id=user_id,
            theme=Theme(self.theme),
            model=self.model or None,  # chuỗi rỗng cũng nghĩa là "dùng model mặc định"
            temperature=self.temperature,
            send_on_enter=self.send_on_enter,
            show_suggestions=self.show_suggestions,
        )


class SettingsResponse(BaseModel):
    """Khuôn bọc ngoài — frontend đọc `payload.settings`."""

    settings: SettingsPayload


class SettingsUpdateRequest(BaseModel):
    """Body của PUT /settings."""

    settings: SettingsPayload
