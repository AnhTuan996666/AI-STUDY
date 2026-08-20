"""Dữ liệu của module auth: tài khoản và token đã thu hồi.

Mỗi bảng có hai lớp:

- `User` / `RevokedToken` — **domain model** (dataclass thuần Python). Tầng service chỉ
  làm việc với lớp này.
- `UserORM` / `RevokedTokenORM` — **ORM model**, mô tả bảng thật trong PostgreSQL.

Tách đôi như vậy để đổi cách lưu trữ (Postgres -> Supabase -> gì khác) không lan lên
tầng nghiệp vụ. Hai hàm `to_domain()` / `from_domain()` là cầu nối duy nhất giữa chúng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcDateTime

EMAIL_MAX_LENGTH = 320
DISPLAY_NAME_MAX_LENGTH = 60


class AuthProvider(StrEnum):
    """Cách tài khoản này được tạo ra."""

    PASSWORD = "password"
    GOOGLE = "google"


def normalize_email(email: str) -> str:
    """Email không phân biệt hoa thường — chuẩn hóa một lần ở biên để so sánh nhất quán."""
    return email.strip().lower()


# ============================ users =====================================


@dataclass
class User:
    """Một tài khoản.

    `password_hash` là None với tài khoản đăng nhập bằng Google — họ không có mật khẩu
    ở hệ thống này, và đó là chuyện bình thường chứ không phải dữ liệu hỏng.
    """

    email: str
    display_name: str
    password_hash: str | None = None
    avatar_url: str | None = None
    provider: AuthProvider = AuthProvider.PASSWORD
    google_sub: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class UserORM(Base):
    """Bảng `users`."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    avatar_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    provider: Mapped[str] = mapped_column(String(32), default=AuthProvider.PASSWORD.value)
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))

    def to_domain(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            display_name=self.display_name,
            password_hash=self.password_hash,
            avatar_url=self.avatar_url,
            provider=AuthProvider(self.provider),
            google_sub=self.google_sub,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserORM:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            avatar_url=user.avatar_url,
            provider=user.provider.value,
            google_sub=user.google_sub,
            created_at=user.created_at,
        )


# ======================== revoked_tokens ================================


@dataclass
class RevokedToken:
    """Một token đã bị thu hồi bởi `POST /auth/logout`.

    Vì sao cần lưu: JWT là **stateless** — đã ký thì tự nó có hiệu lực tới lúc hết hạn,
    server không "xoá" được. Muốn đăng xuất có hiệu lực thật thì phải ghi `jti` lại và
    từ chối nó ở lần dùng sau. Đây là cái giá của việc chọn JWT thay vì session id.
    """

    jti: UUID
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RevokedTokenORM(Base):
    """Bảng `revoked_tokens`. Chỉ lớn bằng số lần đăng xuất trong một chu kỳ hết hạn."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Có cột này mới dọn được rác: hết hạn rồi thì token tự vô hiệu, giữ lại vô nghĩa.
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    revoked_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))

    def to_domain(self) -> RevokedToken:
        return RevokedToken(
            jti=self.jti,
            user_id=self.user_id,
            expires_at=self.expires_at,
            revoked_at=self.revoked_at,
        )

    @classmethod
    def from_domain(cls, token: RevokedToken) -> RevokedTokenORM:
        return cls(
            jti=token.jti,
            user_id=token.user_id,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
