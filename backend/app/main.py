"""Điểm khởi động ứng dụng FastAPI."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# PHẢI đặt TRƯỚC khi uvicorn/asyncio tạo event loop: Windows mặc định dùng
# ProactorEventLoop, nhưng driver psycopg (async) chỉ chạy trên SelectorEventLoop.
# Không có dòng này thì mọi API đụng PostgreSQL sẽ lỗi ngay khi chạy uvicorn.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.router import api_router  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.core.exceptions import register_exception_handlers  # noqa: E402
from app.core.logging import get_logger, setup_logging  # noqa: E402
from app.core.rate_limit import RateLimitMiddleware  # noqa: E402
from app.db.session import create_database  # noqa: E402
from app.modules.auth.google import GoogleOAuthClient  # noqa: E402
from app.modules.auth.repository import (  # noqa: E402
    InMemoryTokenBlocklist,
    InMemoryUserRepository,
)
from app.modules.conversations.repository import (  # noqa: E402
    InMemoryConversationRepository,
    InMemoryMessageRepository,
)
from app.modules.health.schemas import RootResponse  # noqa: E402
from app.modules.llm.providers.factory import create_provider  # noqa: E402
from app.modules.llm.queue.factory import create_queue  # noqa: E402
from app.modules.settings.repository import InMemorySettingsRepository  # noqa: E402

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Khởi tạo provider 1 lần cho cả vòng đời app, dọn dẹp khi tắt."""
    settings: Settings = app.state.settings
    provider = create_provider(settings)
    app.state.llm_provider = provider

    # Hàng đợi dùng chung: chặn số lượt xuống model server để GPU không bị dồn.
    app.state.llm_queue = create_queue(settings)

    app.state.google_oauth = GoogleOAuthClient(settings)

    # Database. Có DATABASE_NAME/DATABASE_URL thì `app/api/deps.py` tự chuyển sang
    # repository chạy PostgreSQL; các bản in-memory dưới đây khi đó không được dùng tới.
    app.state.database = create_database(settings)

    # Bản dự phòng cho lịch sử hội thoại khi chưa cấu hình DB. Conversation repo cần
    # message repo để đếm số tin và xoá theo (SQL thì cascade lo, in-memory phải tự gọi).
    message_repository = InMemoryMessageRepository()
    app.state.message_repository = message_repository
    app.state.conversation_repository = InMemoryConversationRepository(message_repository)

    # Bản dự phòng khi chưa cấu hình DB. Phải là MỘT instance cho cả app, nếu không
    # mỗi request lại đọc ra một kho rỗng.
    app.state.user_repository = InMemoryUserRepository()
    app.state.token_blocklist = InMemoryTokenBlocklist()
    app.state.settings_repository = InMemorySettingsRepository()

    logger.info(
        "Khởi động %s v%s | env=%s | provider=%s | model=%s"
        " | queue=%s (%d song song, chờ tối đa %d)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        provider.name,
        provider.default_model,
        settings.queue_backend,
        settings.llm_max_concurrent,
        settings.llm_max_queue,
    )
    if not await provider.health():
        logger.warning(
            "Model server không phản hồi. Đặt LLM_PROVIDER=mock trong .env để dev "
            "mà không cần Ollama."
        )

    if not settings.has_database:
        logger.warning(
            "Chưa cấu hình database — tài khoản và cài đặt đang lưu trong bộ nhớ và sẽ "
            "MẤT khi restart. Đặt DATABASE_NAME (và DATABASE_PASSWORD) trong .env."
        )

    yield

    await app.state.google_oauth.aclose()
    await app.state.llm_queue.aclose()
    await provider.aclose()
    if app.state.database is not None:
        await app.state.database.aclose()
    logger.info("Đã tắt ứng dụng.")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory — cho phép test dựng app với settings riêng."""
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API chat với model mã nguồn mở tự host.",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    app.add_middleware(RateLimitMiddleware, settings=settings)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False, response_model=RootResponse)
    async def root() -> RootResponse:
        return RootResponse(
            name=settings.app_name,
            version=settings.app_version,
            docs="/docs",
            health=f"{settings.api_prefix}/health",
        )

    return app


app = create_app()
