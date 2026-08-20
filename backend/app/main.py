"""Điểm khởi động ứng dụng FastAPI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import create_database
from app.modules.auth.google import GoogleOAuthClient
from app.modules.auth.repository import InMemoryTokenBlocklist, InMemoryUserRepository
from app.modules.conversations.repository import (
    InMemoryConversationRepository,
    InMemoryMessageRepository,
)
from app.modules.health.schemas import RootResponse
from app.modules.llm.providers.factory import create_provider
from app.modules.llm.queue.factory import create_queue
from app.modules.settings.repository import InMemorySettingsRepository

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

    # Lịch sử hội thoại vẫn nằm ở trình duyệt (FR-05 chưa làm) nên luôn in-memory.
    app.state.conversation_repository = InMemoryConversationRepository()
    app.state.message_repository = InMemoryMessageRepository()

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
