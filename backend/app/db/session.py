"""Quản lý kết nối & session tới database.

`DATABASE_URL` trống -> không dựng engine, app chạy bằng repository in-memory. Nhờ vậy
dev/test không cần Postgres, còn production thì `Settings` đã chặn thiếu biến từ lúc
khởi động (xem `_require_secrets_in_production`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseNotConfiguredError(RuntimeError):
    """Ném ra khi có code cố dùng DB trong khi `DATABASE_URL` chưa đặt."""


class Database:
    """Vòng đời engine + factory session, gắn vào `app.state`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Mở session, tự commit khi xong và rollback khi có lỗi."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def check(self) -> bool:
        """Thử một truy vấn rẻ tiền để biết DB còn sống — dùng cho /health."""
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("select 1"))
            return True
        except SQLAlchemyError:
            logger.warning("Không kết nối được database.")
            return False

    async def aclose(self) -> None:
        await self._engine.dispose()


def create_database(settings: Settings) -> Database | None:
    """Dựng engine; None khi chưa bật DB (xem `Settings.sqlalchemy_url`)."""
    url = settings.sqlalchemy_url
    if not url:
        return None

    engine = create_async_engine(
        url,
        echo=settings.db_echo,
        pool_pre_ping=True,  # kết nối bị Postgres/Supabase cắt sau thời gian rảnh vẫn tự nối lại
    )
    logger.info("Đã cấu hình database: %s", _safe_url(url))
    return Database(engine)


def _safe_url(url: str) -> str:
    """Che mật khẩu trước khi ghi log."""
    if "@" not in url or "://" not in url:
        return url

    scheme, rest = url.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"
