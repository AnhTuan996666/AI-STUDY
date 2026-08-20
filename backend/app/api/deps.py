"""Dependency dùng chung cho mọi module.

Đây là nơi **duy nhất** quyết định "dùng cài đặt cụ thể nào": repository chạy trên
PostgreSQL hay chạy in-memory, provider nào, hàng đợi nào. Router và service chỉ nhìn
thấy interface, nên đổi hạ tầng không phải sửa nghiệp vụ.

Đọc từ trên xuống theo 4 nhóm:
    1. Hạ tầng    — settings, session database, provider, hàng đợi
    2. Repository — đọc/ghi dữ liệu
    3. Service    — nghiệp vụ
    4. Người dùng — ai đang gọi API
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import client_key
from app.core.security import (
    TokenPayload,
    UnauthorizedError,
    decode_access_token,
    extract_bearer_token,
)
from app.db.session import Database
from app.modules.auth.models import User
from app.modules.auth.repository import (
    SqlTokenBlocklist,
    SqlUserRepository,
    TokenBlocklist,
    UserRepository,
)
from app.modules.auth.service import AuthService
from app.modules.chat.service import ChatService
from app.modules.conversations.repository import ConversationRepository, MessageRepository
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.queue.base import RequestQueue
from app.modules.llm.service import ModelService
from app.modules.settings.repository import SettingsRepository, SqlSettingsRepository
from app.modules.settings.service import SettingsService

# ============================ 1. Hạ tầng ================================

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_session(request: Request) -> AsyncIterator[AsyncSession | None]:
    """Mở session cho request, tự commit/rollback. None khi chưa cấu hình DB."""
    database: Database | None = request.app.state.database
    if database is None:
        yield None
        return

    async with database.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession | None, Depends(get_session)]


def get_provider(request: Request) -> LLMProvider:
    """Provider đã khởi tạo sẵn ở lifespan (dùng chung 1 connection pool)."""
    return request.app.state.llm_provider


ProviderDep = Annotated[LLMProvider, Depends(get_provider)]


def get_queue(request: Request) -> RequestQueue:
    """Hàng đợi dùng chung toàn app (khởi tạo ở lifespan)."""
    return request.app.state.llm_queue


QueueDep = Annotated[RequestQueue, Depends(get_queue)]


def get_client_key(request: Request) -> str:
    """Định danh người gọi cho hàng đợi — cùng quy tắc với rate limit."""
    return client_key(request)


ClientKeyDep = Annotated[str, Depends(get_client_key)]


# =========================== 2. Repository ==============================
#
# Có session -> dùng bản PostgreSQL. Không có -> dùng bản in-memory đã tạo sẵn ở
# lifespan (phải dùng chung một instance cho cả app; tạo mới mỗi request thì lần nào
# đọc cũng ra rỗng).


def get_user_repository(request: Request, session: SessionDep) -> UserRepository:
    if session is None:
        return request.app.state.user_repository
    return SqlUserRepository(session)


def get_token_blocklist(request: Request, session: SessionDep) -> TokenBlocklist:
    if session is None:
        return request.app.state.token_blocklist
    return SqlTokenBlocklist(session)


def get_settings_repository(request: Request, session: SessionDep) -> SettingsRepository:
    if session is None:
        return request.app.state.settings_repository
    return SqlSettingsRepository(session)


def get_conversation_repository(request: Request) -> ConversationRepository:
    """Lịch sử hội thoại vẫn in-memory — FR-05 chưa chuyển lên database."""
    return request.app.state.conversation_repository


def get_message_repository(request: Request) -> MessageRepository:
    return request.app.state.message_repository


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenBlocklistDep = Annotated[TokenBlocklist, Depends(get_token_blocklist)]
SettingsRepositoryDep = Annotated[SettingsRepository, Depends(get_settings_repository)]
ConversationRepositoryDep = Annotated[ConversationRepository, Depends(get_conversation_repository)]
MessageRepositoryDep = Annotated[MessageRepository, Depends(get_message_repository)]


# ============================ 3. Service ================================


def get_auth_service(
    users: UserRepositoryDep,
    blocklist: TokenBlocklistDep,
    settings: SettingsDep,
) -> AuthService:
    return AuthService(users=users, blocklist=blocklist, settings=settings)


def get_settings_service(repository: SettingsRepositoryDep) -> SettingsService:
    return SettingsService(repository=repository)


def get_model_service(provider: ProviderDep, settings: SettingsDep) -> ModelService:
    return ModelService(provider=provider, settings=settings)


def get_chat_service(
    provider: ProviderDep,
    settings: SettingsDep,
    queue: QueueDep,
    key: ClientKeyDep,
) -> ChatService:
    return ChatService(provider=provider, settings=settings, queue=queue, client_key=key)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
ModelServiceDep = Annotated[ModelService, Depends(get_model_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


# ========================== 4. Người dùng ===============================


def get_token_payload(request: Request, settings: SettingsDep) -> TokenPayload:
    """Đọc và xác thực chữ ký token. Ném 401 nếu thiếu hoặc hỏng."""
    token = extract_bearer_token(request)
    if token is None:
        raise UnauthorizedError("Cần đăng nhập để dùng chức năng này.")

    return decode_access_token(token, settings)


TokenPayloadDep = Annotated[TokenPayload, Depends(get_token_payload)]


async def get_current_user(payload: TokenPayloadDep, auth: AuthServiceDep) -> User:
    """User đang đăng nhập. Ném 401 nếu token đã đăng xuất hoặc tài khoản đã bị xoá.

    Đây mới là dependency dùng cho endpoint cần bảo vệ — nó tra cả danh sách thu hồi,
    khác với `get_current_user_id` trong `core/security.py` (chỉ xem chữ ký, dành cho
    rate limit ở middleware).
    """
    return await auth.resolve(payload)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
