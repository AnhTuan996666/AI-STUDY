"""Schema request/response cho các endpoint xác thực.

Khuôn phản hồi bám đúng docs/API_CONTRACT.md mục "Auth".
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.auth.models import DISPLAY_NAME_MAX_LENGTH, User

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    """Body của POST /auth/register.

    Frontend đã kiểm trước khi gửi, nhưng client không đáng tin nên kiểm lại ở đây.
    """

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    display_name: str = Field(min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Tên hiển thị không được để trống.")
        return clean


class LoginRequest(BaseModel):
    """Body của POST /auth/login."""

    email: EmailStr
    # Không áp min_length ở đây: mật khẩu cũ có thể ngắn hơn quy định hiện tại, và
    # báo "mật khẩu quá ngắn" khi đăng nhập là tiết lộ thừa.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    """Thông tin tài khoản trả cho frontend. Không bao giờ chứa mật khẩu."""

    id: UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    provider: str
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            provider=user.provider.value,
            created_at=user.created_at,
        )


class AuthResponse(BaseModel):
    """Kết quả của /auth/register và /auth/login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class LogoutResponse(BaseModel):
    """Kết quả của POST /auth/logout."""

    detail: str = "Đã đăng xuất."
