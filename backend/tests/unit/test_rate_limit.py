"""Test thuật toán sliding window (không qua HTTP)."""

from __future__ import annotations

from app.core.rate_limit import SlidingWindowRateLimiter


def test_allows_up_to_max_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("ip-1") == (True, 1)
    assert limiter.allow("ip-1") == (True, 0)
    assert limiter.allow("ip-1") == (False, 0)


def test_isolates_keys() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("ip-1")[0] is True
    assert limiter.allow("ip-2")[0] is True
    assert limiter.allow("ip-1")[0] is False


def test_frees_slots_after_window() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)

    assert limiter.allow("ip-1", now=100.0)[0] is True
    assert limiter.allow("ip-1", now=105.0)[0] is False
    assert limiter.allow("ip-1", now=111.0)[0] is True


def test_reset_clears_all_counters() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    limiter.allow("ip-1")

    limiter.reset()

    assert limiter.allow("ip-1")[0] is True
