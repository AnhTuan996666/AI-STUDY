"""Môi trường chạy migration của Alembic.

Chuỗi kết nối và toàn bộ metadata đều lấy từ code ứng dụng, không khai lại ở đây:

- URL đọc từ `Settings.sqlalchemy_url` (tức là từ .env) — cùng nguồn với app khi chạy.
- Bảng đọc từ `app.db.registry.target_metadata` — nơi gom mọi ORM model.

Nhờ vậy `alembic revision --autogenerate` luôn nhìn thấy đúng những gì app dùng.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings
from app.db.registry import target_metadata

# Windows mặc định dùng ProactorEventLoop, nhưng psycopg (async) chỉ chạy trên
# SelectorEventLoop. Ép policy trước khi asyncio.run() để `alembic upgrade` không lỗi.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

config = context.config
settings = get_settings()

database_url = settings.sqlalchemy_url
if database_url is None:
    raise RuntimeError(
        "Chưa cấu hình database. Đặt DATABASE_NAME (và DATABASE_PASSWORD) hoặc "
        "DATABASE_URL trong backend/.env rồi chạy lại."
    )


def run_migrations_offline() -> None:
    """Sinh SQL mà không cần kết nối thật (chế độ --sql)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,  # phát hiện đổi kiểu cột, không chỉ thêm/bớt cột
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Kết nối thật rồi áp migration."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
