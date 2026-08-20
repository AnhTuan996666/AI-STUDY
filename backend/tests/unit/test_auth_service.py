"""Test nghiệp vụ AuthService (dùng repository in-memory)."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.security import decode_access_token
from app.modules.auth.models import AuthProvider
from app.modules.auth.repository import InMemoryTokenBlocklist, InMemoryUserRepository
from app.modules.auth.service import (
    AuthService,
    EmailTakenError,
    InvalidCredentialsError,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        log_level="WARNING",
        jwt_secret="unit-test-secret-du-dai-cho-32-byte-nhe",
    )


@pytest.fixture
def service(settings: Settings) -> AuthService:
    return AuthService(
        users=InMemoryUserRepository(),
        blocklist=InMemoryTokenBlocklist(),
        settings=settings,
    )


async def test_register_hashes_password(service: AuthService) -> None:
    user, _token = await service.register("a@x.com", "matkhau123", "A")

    assert user.password_hash is not None
    assert user.password_hash != "matkhau123"
    assert user.provider is AuthProvider.PASSWORD


async def test_register_normalizes_email(service: AuthService) -> None:
    user, _ = await service.register("  A@X.COM ", "matkhau123", "A")
    assert user.email == "a@x.com"


async def test_register_duplicate_raises(service: AuthService) -> None:
    await service.register("a@x.com", "matkhau123", "A")
    with pytest.raises(EmailTakenError):
        await service.register("A@x.com", "khac12345", "A2")


async def test_login_wrong_password_raises(service: AuthService) -> None:
    await service.register("a@x.com", "matkhau123", "A")
    with pytest.raises(InvalidCredentialsError):
        await service.login("a@x.com", "sai-mat-khau")


async def test_login_unknown_email_raises(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await service.login("khong-co@x.com", "matkhau123")


async def test_token_carries_the_user_id(service: AuthService, settings: Settings) -> None:
    user, token = await service.register("a@x.com", "matkhau123", "A")

    payload = decode_access_token(token.access_token, settings)
    assert payload.user_id == user.id


async def test_logout_then_resolve_is_rejected(service: AuthService, settings: Settings) -> None:
    _user, token = await service.register("a@x.com", "matkhau123", "A")
    payload = decode_access_token(token.access_token, settings)

    # Trước khi đăng xuất: resolve được.
    assert (await service.resolve(payload)).email == "a@x.com"

    await service.logout(payload)

    from app.core.security import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        await service.resolve(payload)


async def test_google_login_creates_account_when_new(service: AuthService) -> None:
    user, _ = await service.login_with_google(
        google_sub="google-123",
        email="g@x.com",
        display_name="G",
        avatar_url="http://avatar",
    )

    assert user.provider is AuthProvider.GOOGLE
    assert user.password_hash is None
    assert user.google_sub == "google-123"


async def test_google_login_links_to_existing_email(service: AuthService) -> None:
    """Đã có tài khoản mật khẩu cùng email -> gắn Google vào, không tạo tài khoản thứ hai."""
    password_user, _ = await service.register("a@x.com", "matkhau123", "A")

    google_user, _ = await service.login_with_google(
        google_sub="google-xyz",
        email="A@x.com",
        display_name="A",
        avatar_url=None,
    )

    assert google_user.id == password_user.id
    assert google_user.google_sub == "google-xyz"


async def test_google_login_is_stable_across_visits(service: AuthService) -> None:
    """Đăng nhập Google lần hai phải trả về đúng tài khoản cũ, không nhân bản."""
    first, _ = await service.login_with_google("g-1", "g@x.com", "G", None)
    second, _ = await service.login_with_google("g-1", "g@x.com", "G", None)

    assert first.id == second.id
