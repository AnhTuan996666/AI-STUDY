"""Test tiện ích xử lý chuỗi."""

from __future__ import annotations

import pytest

from app.modules.conversations.models import DEFAULT_TITLE
from app.utils.text import derive_title, normalize_whitespace, truncate


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  xin   chào  ", "xin chào"),
        ("dòng 1\n\ndòng 2", "dòng 1 dòng 2"),
        ("\tcó\ttab\t", "có tab"),
        ("", ""),
    ],
)
def test_normalize_whitespace(raw: str, expected: str) -> None:
    assert normalize_whitespace(raw) == expected


def test_truncate_keeps_short_text_untouched() -> None:
    assert truncate("ngắn", 10) == "ngắn"


def test_truncate_adds_suffix_when_cut() -> None:
    assert truncate("abcdefghij", 5) == "abcde…"


def test_truncate_with_non_positive_length() -> None:
    assert truncate("abc", 0) == ""


def test_derive_title_from_first_message() -> None:
    assert derive_title("  Giải thích  REST API  ") == "Giải thích REST API"


def test_derive_title_falls_back_when_blank() -> None:
    assert derive_title("   ") == DEFAULT_TITLE


def test_derive_title_respects_max_length() -> None:
    title = derive_title("a" * 100, max_length=10)

    assert title == "a" * 10 + "…"
