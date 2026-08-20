"""Integration test cho GET/PUT /settings và GET /models."""

from __future__ import annotations

from fastapi.testclient import TestClient

_SETTINGS = "/api/v1/settings"
_MODELS = "/api/v1/models"


def _token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "u@congty.com", "password": "matkhau123", "display_name": "U"},
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_settings_requires_token(client: TestClient) -> None:
    assert client.get(_SETTINGS).status_code == 401


def test_get_settings_returns_defaults_for_new_user(client: TestClient) -> None:
    token = _token(client)
    response = client.get(_SETTINGS, headers=_auth(token))

    assert response.status_code == 200
    settings = response.json()["settings"]
    assert settings["theme"] == "system"
    assert settings["model"] is None
    assert settings["temperature"] == 0.7
    assert settings["send_on_enter"] is True


def test_put_then_get_round_trip(client: TestClient) -> None:
    token = _token(client)

    put = client.put(
        _SETTINGS,
        headers=_auth(token),
        json={
            "settings": {
                "theme": "dark",
                "model": "qwen2.5:7b",
                "temperature": 0.3,
                "send_on_enter": False,
                "show_suggestions": False,
            }
        },
    )
    assert put.status_code == 200
    assert put.json()["settings"]["theme"] == "dark"

    got = client.get(_SETTINGS, headers=_auth(token)).json()["settings"]
    assert got["theme"] == "dark"
    assert got["model"] == "qwen2.5:7b"
    assert got["temperature"] == 0.3
    assert got["send_on_enter"] is False


def test_put_rejects_out_of_range_temperature(client: TestClient) -> None:
    token = _token(client)
    response = client.put(
        _SETTINGS,
        headers=_auth(token),
        json={"settings": {"temperature": 9.0}},
    )
    assert response.status_code == 422


def test_settings_are_isolated_per_user(client: TestClient) -> None:
    first = _token(client)
    client.put(_SETTINGS, headers=_auth(first), json={"settings": {"theme": "dark"}})

    second_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "khac@congty.com", "password": "matkhau123", "display_name": "Khác"},
    )
    second = second_resp.json()["access_token"]

    # User thứ hai vẫn thấy mặc định, không dính cài đặt của user thứ nhất.
    got = client.get(_SETTINGS, headers=_auth(second)).json()["settings"]
    assert got["theme"] == "system"


def test_models_endpoint_is_public(client: TestClient) -> None:
    """Menu chọn model phải dùng được cả khi chưa đăng nhập."""
    response = client.get(_MODELS)

    assert response.status_code == 200
    models = response.json()["models"]
    assert len(models) >= 1
    assert any(model["is_default"] for model in models)
