"""Integration test cho luồng xác thực email/mật khẩu (chạy in-memory)."""

from __future__ import annotations

from fastapi.testclient import TestClient

_REGISTER = "/api/v1/auth/register"
_LOGIN = "/api/v1/auth/login"
_ME = "/api/v1/auth/me"
_LOGOUT = "/api/v1/auth/logout"


def _register(client: TestClient, email: str = "a@congty.com") -> dict:
    response = client.post(
        _REGISTER,
        json={"email": email, "password": "matkhau123", "display_name": "Nguyễn A"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_user(client: TestClient) -> None:
    body = _register(client)

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "a@congty.com"
    assert body["user"]["display_name"] == "Nguyễn A"
    assert body["user"]["provider"] == "password"
    assert "password" not in body["user"]  # không rò mật khẩu ra ngoài


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)
    response = client.post(
        _REGISTER,
        json={"email": "a@congty.com", "password": "khac123456", "display_name": "Khác"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_register_validates_short_password(client: TestClient) -> None:
    response = client.post(
        _REGISTER,
        json={"email": "b@congty.com", "password": "123", "display_name": "B"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_password(client: TestClient) -> None:
    _register(client)
    response = client.post(_LOGIN, json={"email": "a@congty.com", "password": "matkhau123"})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_fails_with_wrong_password(client: TestClient) -> None:
    _register(client)
    response = client.post(_LOGIN, json={"email": "a@congty.com", "password": "sai-roi"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_gives_same_error(client: TestClient) -> None:
    """Không tiết lộ email nào đã đăng ký: cùng mã lỗi với sai mật khẩu."""
    response = client.post(_LOGIN, json={"email": "chua-ton-tai@x.com", "password": "gigicungduoc"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_token(client: TestClient) -> None:
    response = client.get(_ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_returns_flat_user_object(client: TestClient) -> None:
    token = _register(client)["access_token"]
    response = client.get(_ME, headers=_auth_header(token))

    assert response.status_code == 200
    body = response.json()
    # Hợp đồng: /auth/me trả object user TRẦN, không bọc trong { user: ... }.
    assert body["email"] == "a@congty.com"
    assert "user" not in body


def test_logout_revokes_the_token(client: TestClient) -> None:
    token = _register(client)["access_token"]

    assert client.get(_ME, headers=_auth_header(token)).status_code == 200

    logout = client.post(_LOGOUT, headers=_auth_header(token))
    assert logout.status_code == 200

    # Token đã thu hồi thì không dùng lại được.
    assert client.get(_ME, headers=_auth_header(token)).status_code == 401


def test_logout_twice_is_ok(client: TestClient) -> None:
    """Đăng xuất hai lần cùng token vẫn trả 200, không phải 401."""
    token = _register(client)["access_token"]

    assert client.post(_LOGOUT, headers=_auth_header(token)).status_code == 200
    assert client.post(_LOGOUT, headers=_auth_header(token)).status_code == 200
