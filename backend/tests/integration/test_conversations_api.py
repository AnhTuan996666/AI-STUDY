"""Integration test cho nhóm /conversations và việc lưu tin qua /chat/stream (in-memory)."""

from __future__ import annotations

from fastapi.testclient import TestClient

_CONV = "/api/v1/conversations"


def _register(client: TestClient, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "matkhau123", "display_name": "U"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _read_sse(client: TestClient, token: str, body: dict) -> list[str]:
    """Gọi /chat/stream, trả về các dòng nội dung delta."""
    deltas: list[str] = []
    with client.stream("POST", "/api/v1/chat/stream", headers=_auth(token), json=body) as resp:
        assert resp.status_code == 200, resp.read()
        for line in resp.iter_lines():
            if line.startswith("data:"):
                deltas.append(line)
    return deltas


def test_conversations_requires_token(client: TestClient) -> None:
    assert client.get(_CONV).status_code == 401


def test_create_and_list(client: TestClient) -> None:
    token = _register(client, "a@congty.com")

    created = client.post(_CONV, headers=_auth(token), json={"title": "Về REST"})
    assert created.status_code == 201
    conv = created.json()["conversation"]
    assert conv["title"] == "Về REST"
    assert conv["messages"] == []
    assert conv["message_count"] == 0

    listed = client.get(_CONV, headers=_auth(token)).json()["conversations"]
    assert len(listed) == 1
    assert listed[0]["id"] == conv["id"]


def test_get_detail_and_ownership(client: TestClient) -> None:
    owner = _register(client, "owner@congty.com")
    other = _register(client, "other@congty.com")

    conv_id = client.post(_CONV, headers=_auth(owner), json={"title": "Riêng"}).json()[
        "conversation"
    ]["id"]

    assert client.get(f"{_CONV}/{conv_id}", headers=_auth(owner)).status_code == 200
    # Người khác không được xem, và phải là 404 (không phải 403) để không lộ id có tồn tại.
    assert client.get(f"{_CONV}/{conv_id}", headers=_auth(other)).status_code == 404


def test_patch_rename_and_pin(client: TestClient) -> None:
    token = _register(client, "a@congty.com")
    conv_id = client.post(_CONV, headers=_auth(token), json={"title": "Cũ"}).json()["conversation"][
        "id"
    ]

    renamed = client.patch(
        f"{_CONV}/{conv_id}", headers=_auth(token), json={"title": "Mới", "is_pinned": True}
    )
    assert renamed.status_code == 200
    conv = renamed.json()["conversation"]
    assert conv["title"] == "Mới"
    assert conv["is_pinned"] is True


def test_delete(client: TestClient) -> None:
    token = _register(client, "a@congty.com")
    conv_id = client.post(_CONV, headers=_auth(token), json={"title": "Xoá đi"}).json()[
        "conversation"
    ]["id"]

    assert client.delete(f"{_CONV}/{conv_id}", headers=_auth(token)).status_code == 204
    assert client.get(f"{_CONV}/{conv_id}", headers=_auth(token)).status_code == 404


def test_stream_persists_messages_when_logged_in(client: TestClient) -> None:
    token = _register(client, "a@congty.com")
    conv_id = client.post(_CONV, headers=_auth(token), json={"title": "Chat"}).json()[
        "conversation"
    ]["id"]

    _read_sse(
        client,
        token,
        {
            "messages": [{"role": "user", "content": "Xin chào"}],
            "conversation_id": conv_id,
        },
    )

    # Sau khi stream xong: hội thoại phải có 2 tin (user + assistant).
    detail = client.get(f"{_CONV}/{conv_id}", headers=_auth(token)).json()["conversation"]
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "Xin chào"
    assert detail["message_count"] == 2


def test_stream_to_someone_elses_conversation_is_404(client: TestClient) -> None:
    owner = _register(client, "owner@congty.com")
    other = _register(client, "other@congty.com")
    conv_id = client.post(_CONV, headers=_auth(owner), json={"title": "Riêng"}).json()[
        "conversation"
    ]["id"]

    resp = client.post(
        "/api/v1/chat/stream",
        headers=_auth(other),
        json={"messages": [{"role": "user", "content": "hi"}], "conversation_id": conv_id},
    )
    assert resp.status_code == 404


def test_guest_stream_still_works_without_saving(client: TestClient) -> None:
    """Khách (không token) vẫn chat được; chỉ là không lưu."""
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    ) as resp:
        assert resp.status_code == 200
        resp.read()
