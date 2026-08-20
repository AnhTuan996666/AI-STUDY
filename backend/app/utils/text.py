"""Tiện ích xử lý chuỗi dùng chung."""

from __future__ import annotations

import re

from app.modules.conversations.models import DEFAULT_TITLE, TITLE_MAX_LENGTH

_WHITESPACE = re.compile(r"\s+")
_ELLIPSIS = "…"


def normalize_whitespace(text: str) -> str:
    """Gộp mọi khoảng trắng liên tiếp thành một dấu cách và cắt hai đầu."""
    return _WHITESPACE.sub(" ", text).strip()


def truncate(text: str, max_length: int, suffix: str = _ELLIPSIS) -> str:
    """Cắt chuỗi về tối đa `max_length` ký tự, thêm hậu tố nếu bị cắt."""
    if max_length <= 0:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def derive_title(first_message: str, max_length: int = TITLE_MAX_LENGTH) -> str:
    """Sinh tiêu đề hội thoại từ tin nhắn đầu tiên của người dùng (FR-07).

    Frontend đang làm việc này phía client; hàm ở đây để dùng khi chuyển sang
    lưu hội thoại dưới DB.
    """
    clean = normalize_whitespace(first_message)
    if not clean:
        return DEFAULT_TITLE
    return truncate(clean, max_length)
