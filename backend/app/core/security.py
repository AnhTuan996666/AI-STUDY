"""Bảo mật: băm mật khẩu và cấp/kiểm token truy cập.

Mô hình phiên: **JWT bearer** (theo docs/API_CONTRACT.md). Backend ký token HS256, client
gửi lại ở header `Authorization: Bearer <token>`.

Hai điều cần nhớ về JWT:

1. Token **không thu hồi được** bằng cách xoá ở server — đã ký là có hiệu lực tới lúc hết
   hạn. `POST /auth/logout` vì thế phải ghi `jti` vào bảng `revoked_tokens`
   (xem `app/models/token.py`), và mọi chỗ xác thực phải tra bảng đó.
2. Đổi `JWT_SECRET` = vô hiệu hoá toàn bộ token đang lưu hành. Không đặt biến này thì
   dev sẽ được cấp một khoá ngẫu nhiên mỗi lần khởi động, tức là restart backend là
   mọi người bị đăng xuất.

Mật khẩu băm bằng Argon2id (`argon2-cffi`) — không lưu mật khẩu gốc ở bất cứ đâu.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Request, status

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_BEARER_PREFIX = "bearer "
_hasher = PasswordHasher()

# Khoá ngẫu nhiên cho môi trường dev chưa đặt JWT_SECRET. Sinh một lần cho cả tiến trình
# để token còn sống qua các lần reload của uvicorn trong cùng phiên chạy.
_DEV_SECRET = secrets.token_urlsafe(48)


class UnauthorizedError(AppError):
    """Token thiếu, hỏng, hết hạn hoặc đã bị thu hồi."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


@dataclass(frozen=True)
class TokenPayload:
    """Phần ruột của một access token đã được xác thực chữ ký."""

    user_id: UUID
    jti: UUID
    expires_at: datetime


@dataclass(frozen=True)
class IssuedToken:
    """Token vừa cấp, kèm thông tin để trả về theo hợp đồng API."""

    access_token: str
    expires_in: int
    jti: UUID


# --- mật khẩu -----------------------------------------------------------


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """So mật khẩu với bản băm. False (không ném lỗi) nếu sai hoặc hash hỏng.

    `password_hash=None` là tài khoản đăng nhập bằng Google — không có mật khẩu để so.
    """
    if not password_hash:
        return False

    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True khi hash được tạo bằng tham số cũ hơn cấu hình hiện tại."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


# --- token --------------------------------------------------------------


def jwt_secret(settings: Settings) -> str:
    """Khoá ký. Thiếu cấu hình thì dùng khoá dev ngẫu nhiên và cảnh báo."""
    if settings.jwt_secret:
        return settings.jwt_secret

    logger.warning(
        "Chưa đặt JWT_SECRET — đang dùng khoá ngẫu nhiên của phiên chạy này. "
        "Restart backend là mọi người bị đăng xuất. Đặt JWT_SECRET trong .env."
    )
    return _DEV_SECRET


def create_access_token(user_id: UUID, settings: Settings) -> IssuedToken:
    """Cấp access token cho một user."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.jwt_expires_seconds)
    token_id = uuid4()

    token = jwt.encode(
        {
            "sub": str(user_id),
            "jti": str(token_id),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        jwt_secret(settings),
        algorithm=settings.jwt_algorithm,
    )
    return IssuedToken(
        access_token=token,
        expires_in=settings.jwt_expires_seconds,
        jti=token_id,
    )


def decode_access_token(token: str, settings: Settings) -> TokenPayload:
    """Xác thực chữ ký + hạn dùng. Ném `UnauthorizedError` nếu không hợp lệ.

    KHÔNG kiểm tra danh sách thu hồi ở đây — việc đó cần DB nên nằm ở tầng dependency
    (`app/api/deps.py`).
    """
    try:
        claims = jwt.decode(token, jwt_secret(settings), algorithms=[settings.jwt_algorithm])
        return TokenPayload(
            user_id=UUID(claims["sub"]),
            jti=UUID(claims["jti"]),
            expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Token không hợp lệ. Hãy đăng nhập lại.") from exc


# --- đọc token từ request -----------------------------------------------


def extract_bearer_token(request: Request) -> str | None:
    """Lấy token từ header `Authorization: Bearer <token>`; None nếu không có."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith(_BEARER_PREFIX):
        return None

    token = header[len(_BEARER_PREFIX) :].strip()
    return token or None


def get_current_user_id(request: Request) -> UUID | None:
    """Định danh người gọi, **không** tra DB — dùng cho rate limit ở middleware.

    Chỉ xác thực chữ ký và hạn dùng. Token đã đăng xuất vẫn lọt qua hàm này, chấp nhận
    được vì rate limit chỉ cần một khóa để đếm. Endpoint cần chắc chắn thì dùng
    `CurrentUserDep` trong `app/api/deps.py` (có tra danh sách thu hồi).

    Trả None khi không có token hoặc token hỏng — người gọi tự lùi về phương án theo IP.
    """
    token = extract_bearer_token(request)
    if token is None:
        return None

    # Dùng `scope.get` chứ không `request.app`: middleware/test có thể gọi hàm này với
    # scope chưa gắn app, và khi đó `request.app` ném KeyError chứ không trả None.
    app = request.scope.get("app")
    settings: Settings | None = getattr(getattr(app, "state", None), "settings", None)
    if settings is None:
        return None

    try:
        return decode_access_token(token, settings).user_id
    except UnauthorizedError:
        return None
