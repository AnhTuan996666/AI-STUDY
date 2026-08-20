"""Địa chỉ API của module auth.

    POST /auth/register          tạo tài khoản
    POST /auth/login             đăng nhập bằng email + mật khẩu
    GET  /auth/me                thông tin tài khoản đang đăng nhập
    POST /auth/logout            thu hồi token hiện tại
    GET  /auth/google/authorize  bắt đầu đăng nhập Google
    GET  /auth/google/callback   Google gọi lại sau khi người dùng đồng ý

Khuôn phản hồi: docs/API_CONTRACT.md mục "Auth".
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import AuthServiceDep, CurrentUserDep, TokenPayloadDep
from app.core.logging import get_logger
from app.core.security import IssuedToken
from app.modules.auth.google import GoogleOAuthClient
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    UserResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
)
async def register(payload: RegisterRequest, auth: AuthServiceDep) -> AuthResponse:
    """FR-01 — tạo tài khoản và cấp token luôn, không bắt đăng nhập lại."""
    user, token = await auth.register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return _auth_response(user, token)


@router.post("/login", response_model=AuthResponse, summary="Đăng nhập")
async def login(payload: LoginRequest, auth: AuthServiceDep) -> AuthResponse:
    """FR-01 — sai email hoặc sai mật khẩu đều trả cùng một thông báo."""
    user, token = await auth.login(email=payload.email, password=payload.password)
    return _auth_response(user, token)


@router.get("/me", response_model=UserResponse, summary="Tài khoản đang đăng nhập")
async def me(user: CurrentUserDep) -> UserResponse:
    """Frontend gọi lúc mở app để xác nhận token còn sống."""
    return UserResponse.from_domain(user)


@router.post("/logout", response_model=LogoutResponse, summary="Đăng xuất")
async def logout(payload: TokenPayloadDep, auth: AuthServiceDep) -> LogoutResponse:
    """Thu hồi token hiện tại.

    Dùng `TokenPayloadDep` chứ không phải `CurrentUserDep`: token đã thu hồi mà bấm
    đăng xuất lần nữa thì vẫn nên trả 200, không nên báo 401.
    """
    await auth.logout(payload)
    return LogoutResponse()


# --------------------------- Google OAuth ------------------------------


@router.get(
    "/google/authorize",
    summary="Bắt đầu đăng nhập Google",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def google_authorize(
    request: Request,
    redirect_uri: str = Query(description="Trang callback của frontend"),
) -> RedirectResponse:
    """FR-02 — chuyển hướng sang màn hình đồng ý của Google.

    Phải là điều hướng cả trang (không phải fetch): Google chặn nạp trang đồng ý
    trong iframe/XHR.
    """
    client: GoogleOAuthClient = request.app.state.google_oauth
    return RedirectResponse(client.authorize_url(redirect_uri))


@router.get(
    "/google/callback",
    summary="Google gọi lại sau khi người dùng đồng ý",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def google_callback(
    request: Request,
    auth: AuthServiceDep,
    state: str = Query(description="State do backend ký ở bước authorize"),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None, description="Có giá trị khi người dùng từ chối"),
) -> RedirectResponse:
    """Đổi mã lấy tài khoản, cấp token, rồi trả người dùng về frontend.

    Token đi kèm ở **query string** của `redirect_uri`. Trang callback phía frontend
    đọc token, lưu lại, rồi xoá khỏi thanh địa chỉ (`history.replaceState`) để token
    không nằm lại trong lịch sử trình duyệt.
    """
    client: GoogleOAuthClient = request.app.state.google_oauth
    redirect_uri = client.decode_state(state)

    # Người dùng bấm "Huỷ" ở màn hình Google -> đưa về frontend kèm lý do, không 500.
    if error or not code:
        logger.info("Người dùng huỷ đăng nhập Google: %s", error)
        return RedirectResponse(f"{redirect_uri}?{urlencode({'error': error or 'access_denied'})}")

    profile = await client.exchange(code)
    _user, token = await auth.login_with_google(
        google_sub=profile.sub,
        email=profile.email,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
    )

    query = urlencode(
        {
            "access_token": token.access_token,
            "token_type": "bearer",
            "expires_in": token.expires_in,
        }
    )
    return RedirectResponse(f"{redirect_uri}?{query}")


def _auth_response(user: User, token: IssuedToken) -> AuthResponse:
    """Gói user + token theo đúng khuôn hợp đồng."""
    return AuthResponse(
        access_token=token.access_token,
        expires_in=token.expires_in,
        user=UserResponse.from_domain(user),
    )
