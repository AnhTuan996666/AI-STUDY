"""Đăng nhập bằng Google (OAuth 2.0 Authorization Code).

Luồng đi qua 6 bước:

    1. Trình duyệt vào  GET /auth/google/authorize?redirect_uri=<trang callback của FE>
    2. Backend chuyển hướng sang màn hình đồng ý của Google
    3. Người dùng bấm đồng ý
    4. Google gọi lại  GET /auth/google/callback?code=...&state=...
    5. Backend đổi `code` lấy access token, rồi hỏi Google xem đây là ai
    6. Backend cấp JWT của mình và chuyển hướng về `redirect_uri` kèm token

Hai điểm bảo mật đáng chú ý:

- `state` là một JWT ngắn hạn do chính backend ký, bên trong chứa `redirect_uri`.
  Nhờ vậy không cần lưu state ở server mà vẫn chống được CSRF, và kẻ tấn công không
  sửa được nơi token sẽ bị gửi tới.
- `redirect_uri` bắt buộc phải nằm trong `CORS_ORIGINS`. Thiếu kiểm tra này thì đây là
  một lỗ hổng open redirect: ai cũng gửi được token của người dùng sang tên miền lạ.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from fastapi import status

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import jwt_secret

logger = get_logger(__name__)

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_SCOPES = "openid email profile"
_STATE_TTL_SECONDS = 600  # 10 phút: đủ để đăng nhập, đủ ngắn để state cũ vô dụng


class GoogleOAuthDisabledError(AppError):
    """Chưa khai GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "google_oauth_disabled"


class GoogleOAuthError(AppError):
    """Google từ chối hoặc trả về dữ liệu không dùng được."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "google_oauth_failed"


class InvalidRedirectError(AppError):
    """`redirect_uri` không nằm trong danh sách cho phép."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_redirect_uri"


@dataclass(frozen=True)
class GoogleProfile:
    """Thông tin tài khoản Google, đã lọc còn đúng thứ cần dùng."""

    sub: str
    email: str
    display_name: str
    avatar_url: str | None


class GoogleOAuthClient:
    """Bọc các lời gọi tới Google. Không biết gì về User hay database."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=10.0))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    # --- bước 1-2: dựng URL đồng ý ---------------------------------------

    def authorize_url(self, redirect_uri: str) -> str:
        """URL màn hình đồng ý của Google, kèm `state` đã ký."""
        self._require_enabled()
        self._require_allowed_redirect(redirect_uri)

        query = urlencode(
            {
                "client_id": self._settings.google_client_id,
                "redirect_uri": self._settings.google_redirect_uri,
                "response_type": "code",
                "scope": _SCOPES,
                "state": self._encode_state(redirect_uri),
                "access_type": "online",
                # Luôn hỏi lại tài khoản: máy dùng chung mà nhớ phiên cũ là phiền.
                "prompt": "select_account",
            }
        )
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"

    # --- bước 5: đổi code lấy thông tin người dùng -----------------------

    async def exchange(self, code: str) -> GoogleProfile:
        """Đổi `code` lấy access token rồi hỏi Google xem đây là ai."""
        self._require_enabled()

        try:
            token_response = await self._http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "redirect_uri": self._settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Đổi mã Google thất bại: %s", exc)
            raise GoogleOAuthError("Không đổi được mã đăng nhập với Google. Hãy thử lại.") from exc

        if not access_token:
            raise GoogleOAuthError("Google không trả về access token.")

        try:
            profile_response = await self._http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            payload = profile_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Không lấy được hồ sơ Google: %s", exc)
            raise GoogleOAuthError("Không lấy được thông tin tài khoản Google.") from exc

        return _to_profile(payload)

    # --- state ------------------------------------------------------------

    def _encode_state(self, redirect_uri: str) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "redirect_uri": redirect_uri,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=_STATE_TTL_SECONDS)).timestamp()),
            },
            jwt_secret(self._settings),
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_state(self, state: str) -> str:
        """Lấy lại `redirect_uri` từ state. Ném lỗi nếu state hỏng hoặc quá hạn."""
        try:
            claims = jwt.decode(
                state,
                jwt_secret(self._settings),
                algorithms=[self._settings.jwt_algorithm],
            )
            redirect_uri = str(claims["redirect_uri"])
        except (jwt.InvalidTokenError, KeyError) as exc:
            raise InvalidRedirectError(
                "Phiên đăng nhập Google không hợp lệ hoặc đã quá hạn. Hãy thử lại."
            ) from exc

        # Kiểm lại lần nữa: cấu hình CORS có thể đã đổi kể từ lúc phát state.
        self._require_allowed_redirect(redirect_uri)
        return redirect_uri

    # --- internals --------------------------------------------------------

    def _require_enabled(self) -> None:
        if not self._settings.has_google_oauth:
            raise GoogleOAuthDisabledError(
                "Đăng nhập bằng Google chưa được bật. Cần khai GOOGLE_CLIENT_ID và "
                "GOOGLE_CLIENT_SECRET trong .env của backend."
            )

    def _require_allowed_redirect(self, redirect_uri: str) -> None:
        """Chỉ cho phép quay về đúng những origin đã khai ở CORS_ORIGINS."""
        parsed = urlparse(redirect_uri)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin not in self._settings.cors_origins:
            logger.warning("Chặn redirect_uri lạ: %s", redirect_uri)
            raise InvalidRedirectError(
                "Địa chỉ chuyển hướng không được phép. Kiểm tra CORS_ORIGINS ở backend."
            )


def _to_profile(payload: dict[str, object]) -> GoogleProfile:
    """Chuyển phản hồi userinfo của Google sang khuôn của mình."""
    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise GoogleOAuthError("Tài khoản Google không có email công khai.")

    name = str(payload.get("name") or "").strip()
    return GoogleProfile(
        sub=str(sub),
        email=str(email),
        display_name=name or str(email).split("@")[0],
        avatar_url=str(payload["picture"]) if payload.get("picture") else None,
    )
