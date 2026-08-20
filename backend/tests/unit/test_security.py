"""Test lớp bảo mật: đọc bearer token, băm mật khẩu, cấp/kiểm JWT."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.config import Settings
from app.core.security import (
    UnauthorizedError,
    create_access_token,
    decode_access_token,
    extract_bearer_token,
    get_current_user_id,
    hash_password,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        log_level="WARNING",
        jwt_secret="test-secret-khong-dung-that-nhung-du-32-byte-cho-sha256",
        jwt_expires_seconds=3600,
    )


def _request(headers: dict[str, str] | None = None, settings: Settings | None = None) -> Request:
    raw = Headers(headers or {}).raw
    scope: dict[str, object] = {"type": "http", "method": "GET", "path": "/", "headers": raw}

    if settings is not None:
        # Giả lập `request.app.state.settings` mà không phải dựng cả app.
        class _State:
            pass

        state = _State()
        state.settings = settings  # type: ignore[attr-defined]
        app = _State()
        app.state = state  # type: ignore[attr-defined]
        scope["app"] = app

    return Request(scope)


# --- đọc header ---------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc.def.ghi", "abc.def.ghi"),
        ("bearer abc", "abc"),
        ("BEARER   abc  ", "abc"),
    ],
)
def test_extract_bearer_token(header: str, expected: str) -> None:
    assert extract_bearer_token(_request({"authorization": header})) == expected


@pytest.mark.parametrize("header", ["", "Basic abc", "Bearer", "Bearer    "])
def test_extract_bearer_token_returns_none(header: str) -> None:
    headers = {"authorization": header} if header else {}
    assert extract_bearer_token(_request(headers)) is None


# --- mật khẩu -----------------------------------------------------------


def test_password_round_trip() -> None:
    hashed = hash_password("matkhau123")

    assert hashed != "matkhau123"  # không bao giờ lưu mật khẩu gốc
    assert verify_password("matkhau123", hashed)
    assert not verify_password("sai-mat-khau", hashed)


def test_same_password_gives_different_hashes() -> None:
    """Argon2 tự thêm salt — hai lần băm phải khác nhau."""
    assert hash_password("matkhau123") != hash_password("matkhau123")


def test_verify_password_handles_accounts_without_password() -> None:
    """Tài khoản Google không có mật khẩu -> luôn False, không nổ lỗi."""
    assert not verify_password("bat-ky", None)
    assert not verify_password("bat-ky", "khong-phai-hash-argon2")


# --- token --------------------------------------------------------------


def test_token_round_trip(settings: Settings) -> None:
    user_id = uuid4()

    issued = create_access_token(user_id, settings)
    payload = decode_access_token(issued.access_token, settings)

    assert payload.user_id == user_id
    assert payload.jti == issued.jti
    assert issued.expires_in == settings.jwt_expires_seconds


def test_each_token_has_its_own_jti(settings: Settings) -> None:
    """Cần thiết cho đăng xuất: thu hồi phiên này không được giết phiên khác."""
    user_id = uuid4()

    first = create_access_token(user_id, settings)
    second = create_access_token(user_id, settings)

    assert first.jti != second.jti


def test_expired_token_is_rejected(settings: Settings) -> None:
    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "exp": int((datetime.now(UTC) - timedelta(seconds=10)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(expired, settings)


def test_token_signed_with_another_secret_is_rejected(settings: Settings) -> None:
    forged = jwt.encode(
        {
            "sub": str(uuid4()),
            "jti": str(uuid4()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        "khoa-cua-ke-tan-cong",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(forged, settings)


@pytest.mark.parametrize("token", ["khong-phai-jwt", "a.b.c", ""])
def test_garbage_token_is_rejected(settings: Settings, token: str) -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token(token, settings)


# --- đọc user từ request (dùng cho rate limit) ---------------------------


def test_get_current_user_id_reads_valid_token(settings: Settings) -> None:
    user_id = uuid4()
    issued = create_access_token(user_id, settings)

    request = _request({"authorization": f"Bearer {issued.access_token}"}, settings)

    assert get_current_user_id(request) == user_id


def test_get_current_user_id_returns_none_without_valid_token(settings: Settings) -> None:
    """Không có token hoặc token hỏng -> None để người gọi lùi về phương án theo IP."""
    assert get_current_user_id(_request(settings=settings)) is None
    assert get_current_user_id(_request({"authorization": "Bearer hong"}, settings)) is None
    # Scope chưa gắn app (middleware gọi sớm) cũng không được nổ lỗi.
    assert get_current_user_id(_request({"authorization": "Bearer abc"})) is None
