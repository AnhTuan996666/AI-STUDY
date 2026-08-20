"""Đọc/ghi dữ liệu của module auth.

Mỗi kho dữ liệu có 3 phần, theo đúng thứ tự trong file:

1. **Interface** (`UserRepository`, `TokenBlocklist`) — hợp đồng mà tầng service dùng.
2. **Bản PostgreSQL** (`Sql...`) — chạy thật.
3. **Bản in-memory** (`InMemory...`) — dùng khi chưa đặt DATABASE_NAME, cho dev/test.
   KHÔNG dùng ở production: dữ liệu mất khi restart, không chia sẻ giữa nhiều worker.

Service chỉ phụ thuộc phần 1, nên đổi kho lưu trữ không phải sửa nghiệp vụ (NFR-04).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import (
    RevokedToken,
    RevokedTokenORM,
    User,
    UserORM,
    normalize_email,
)


class UserRepository(ABC):
    """CRUD tài khoản — phục vụ FR-01, FR-02."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Lưu tài khoản mới, trả về bản đã lưu."""

    @abstractmethod
    async def get(self, user_id: UUID) -> User | None:
        """Lấy 1 tài khoản theo id; None nếu không tồn tại."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Tìm theo email đã chuẩn hóa (chữ thường); None nếu không có."""

    @abstractmethod
    async def get_by_google_sub(self, google_sub: str) -> User | None:
        """Tìm theo định danh Google (`sub` trong token của Google)."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Ghi đè thông tin tài khoản đã tồn tại."""


class TokenBlocklist(ABC):
    """Danh sách token đã thu hồi — phục vụ `POST /auth/logout`.

    Xem docstring của `RevokedToken` để biết vì sao JWT bắt buộc phải có lớp này.
    """

    @abstractmethod
    async def revoke(self, token: RevokedToken) -> None:
        """Ghi nhận một token không còn dùng được."""

    @abstractmethod
    async def is_revoked(self, jti: UUID) -> bool:
        """True nếu token đã bị thu hồi."""

    @abstractmethod
    async def purge_expired(self) -> int:
        """Dọn các dòng đã quá hạn, trả về số dòng đã xóa."""


# ========================= bản PostgreSQL ===============================


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        row = UserORM.from_domain(user)
        self._session.add(row)
        await self._session.flush()
        return row.to_domain()

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserORM, user_id)
        return row.to_domain() if row else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == normalize_email(email))
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row.to_domain() if row else None

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(UserORM).where(UserORM.google_sub == google_sub)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row.to_domain() if row else None

    async def update(self, user: User) -> User:
        row = await self._session.get(UserORM, user.id)
        if row is None:
            raise LookupError(f"Không tìm thấy user {user.id}")

        row.email = user.email
        row.display_name = user.display_name
        row.password_hash = user.password_hash
        row.avatar_url = user.avatar_url
        row.provider = user.provider.value
        row.google_sub = user.google_sub
        await self._session.flush()
        return row.to_domain()


class SqlTokenBlocklist(TokenBlocklist):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revoke(self, token: RevokedToken) -> None:
        # Đăng xuất hai lần cùng một token là chuyện bình thường -> bỏ qua, không lỗi.
        if await self._session.get(RevokedTokenORM, token.jti) is not None:
            return

        self._session.add(RevokedTokenORM.from_domain(token))
        await self._session.flush()

    async def is_revoked(self, jti: UUID) -> bool:
        stmt = select(RevokedTokenORM.jti).where(RevokedTokenORM.jti == jti)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def purge_expired(self) -> int:
        stmt = delete(RevokedTokenORM).where(RevokedTokenORM.expires_at <= datetime.now(UTC))
        result = await self._session.execute(stmt)
        return result.rowcount or 0


# ========================= bản in-memory ================================


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, User] = {}

    async def create(self, user: User) -> User:
        self._items[user.id] = user
        return user

    async def get(self, user_id: UUID) -> User | None:
        return self._items.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        target = normalize_email(email)
        return next((u for u in self._items.values() if u.email == target), None)

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        return next((u for u in self._items.values() if u.google_sub == google_sub), None)

    async def update(self, user: User) -> User:
        if user.id not in self._items:
            raise LookupError(f"Không tìm thấy user {user.id}")

        self._items[user.id] = user
        return user

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()


class InMemoryTokenBlocklist(TokenBlocklist):
    def __init__(self) -> None:
        self._items: dict[UUID, RevokedToken] = {}

    async def revoke(self, token: RevokedToken) -> None:
        self._items.setdefault(token.jti, token)

    async def is_revoked(self, jti: UUID) -> bool:
        return jti in self._items

    async def purge_expired(self) -> int:
        now = datetime.now(UTC)
        expired = [jti for jti, token in self._items.items() if token.expires_at <= now]
        for jti in expired:
            del self._items[jti]
        return len(expired)

    def clear(self) -> None:
        """Chỉ dùng trong test."""
        self._items.clear()
