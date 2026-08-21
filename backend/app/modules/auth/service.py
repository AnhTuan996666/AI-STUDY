"""Nghiệp vụ xác thực: đăng ký, đăng nhập, đăng xuất, đọc thông tin tài khoản.

Tầng này KHÔNG biết gì về HTTP — không đọc header, không set status code. Nhờ vậy thêm
cách đăng nhập mới (Google, Microsoft…) chỉ là thêm một hàm ở đây (FR-01, FR-02).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import (
    IssuedToken,
    TokenPayload,
    UnauthorizedError,
    create_access_token,
    decode_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.modules.auth.models import AuthProvider, RevokedToken, User, normalize_email
from app.modules.auth.repository import TokenBlocklist, UserRepository

logger = get_logger(__name__)


class EmailTakenError(AppError):
    """Email đã có tài khoản."""

    status_code = status.HTTP_409_CONFLICT
    code = "email_taken"


class InvalidCredentialsError(AppError):
    """Sai email hoặc sai mật khẩu."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_credentials"


class AuthService:
    """Điều phối vòng đời một phiên đăng nhập."""

    def __init__(
        self,
        users: UserRepository,
        blocklist: TokenBlocklist,
        settings: Settings,
    ) -> None:
        self._users = users
        self._blocklist = blocklist
        self._settings = settings

    # --- đăng ký / đăng nhập ---------------------------------------------

    async def register(
        self, email: str, password: str, display_name: str
    ) -> tuple[User, IssuedToken]:
        """Tạo tài khoản mới rồi cấp token luôn (đăng ký xong là đã đăng nhập)."""
        normalized = normalize_email(email)
        if await self._users.get_by_email(normalized) is not None:
            raise EmailTakenError("Email này đã có tài khoản. Hãy đăng nhập hoặc dùng email khác.")

        user = await self._users.create(
            User(
                email=normalized,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                provider=AuthProvider.PASSWORD,
            )
        )
        logger.info("auth.register user=%s", user.id)
        return user, create_access_token(user.id, self._settings)

    async def login(self, email: str, password: str) -> tuple[User, IssuedToken]:
        """Kiểm mật khẩu rồi cấp token."""
        user = await self._users.get_by_email(email)

        # Cùng một thông báo cho "email không tồn tại" và "sai mật khẩu": tách hai
        # trường hợp ra là giúp kẻ tấn công dò được email nào đã đăng ký.
        if user is None or not verify_password(password, user.password_hash):
            logger.info("auth.login.failed email=%s", normalize_email(email))
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng.")

        await self._upgrade_hash_if_needed(user, password)
        logger.info("auth.login user=%s", user.id)
        return user, create_access_token(user.id, self._settings)

    async def login_with_google(
        self,
        google_sub: str,
        email: str,
        display_name: str,
        avatar_url: str | None,
    ) -> tuple[User, IssuedToken]:
        """Đăng nhập bằng Google: có tài khoản thì dùng lại, chưa có thì tạo mới.

        Ba trường hợp, theo thứ tự ưu tiên:
        1. Đã từng đăng nhập Google -> khớp theo `google_sub` (ổn định kể cả khi đổi email).
        2. Đã có tài khoản email/mật khẩu cùng email -> **gắn** Google vào tài khoản đó
           thay vì tạo tài khoản thứ hai trùng email.
        3. Chưa có gì -> tạo mới, không mật khẩu.
        """
        normalized = normalize_email(email)

        user = await self._users.get_by_google_sub(google_sub)
        if user is None:
            existing = await self._users.get_by_email(normalized)
            if existing is not None:
                existing.google_sub = google_sub
                existing.avatar_url = existing.avatar_url or avatar_url
                user = await self._users.update(existing)
                logger.info("auth.google.linked user=%s", user.id)
            else:
                user = await self._users.create(
                    User(
                        email=normalized,
                        display_name=display_name.strip() or normalized.split("@")[0],
                        password_hash=None,
                        avatar_url=avatar_url,
                        provider=AuthProvider.GOOGLE,
                        google_sub=google_sub,
                    )
                )
                logger.info("auth.google.register user=%s", user.id)

        return user, create_access_token(user.id, self._settings)

    # --- phiên hiện tại ---------------------------------------------------

    async def resolve(self, payload: TokenPayload) -> User:
        """Đổi token đã xác thực chữ ký thành User, có kiểm danh sách thu hồi."""
        if await self._blocklist.is_revoked(payload.jti):
            raise UnauthorizedError("Phiên đã đăng xuất. Hãy đăng nhập lại.")

        user = await self._users.get(payload.user_id)
        if user is None:
            # Token còn hạn nhưng tài khoản đã bị xoá.
            raise UnauthorizedError("Tài khoản không còn tồn tại.")

        return user

    async def resolve_optional(self, token: str | None) -> User | None:
        """User từ một bearer token thô, hoặc None nếu thiếu/hỏng/hết hạn/đã đăng xuất.

        Dùng cho endpoint cho phép cả khách (vd /chat). Giải mã bằng CHÍNH settings của
        service — cùng nguồn với lúc cấp token — nên không bao giờ lệch khoá ký.
        """
        if not token:
            return None
        try:
            payload = decode_access_token(token, self._settings)
            return await self.resolve(payload)
        except UnauthorizedError:
            return None

    async def logout(self, payload: TokenPayload) -> None:
        """Thu hồi token hiện tại. Gọi lại lần nữa vẫn an toàn."""
        await self._blocklist.revoke(
            RevokedToken(
                jti=payload.jti,
                user_id=payload.user_id,
                expires_at=payload.expires_at,
            )
        )
        # Dọn rác ngay tại đây: bảng chỉ phình khi có người đăng xuất, nên dọn đúng
        # lúc đó là đủ, khỏi cần cron riêng.
        purged = await self._blocklist.purge_expired()
        logger.info("auth.logout user=%s purged=%d", payload.user_id, purged)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._users.get(user_id)

    # --- internals --------------------------------------------------------

    async def _upgrade_hash_if_needed(self, user: User, password: str) -> None:
        """Băm lại mật khẩu khi tham số Argon2 đã đổi — người dùng không cần biết."""
        if not user.password_hash or not needs_rehash(user.password_hash):
            return

        user.password_hash = hash_password(password)
        await self._users.update(user)
        logger.info("auth.rehash user=%s", user.id)
