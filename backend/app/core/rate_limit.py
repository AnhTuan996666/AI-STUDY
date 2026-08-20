"""Rate limit in-memory theo sliding window.

Giới hạn: chỉ đúng trong 1 process. Khi scale nhiều instance thì thay bằng Redis
(giữ nguyên interface `SlidingWindowRateLimiter.allow`).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.exceptions import error_payload
from app.core.security import get_current_user_id


class SlidingWindowRateLimiter:
    """Đếm số request của từng key trong cửa sổ thời gian trượt."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Trả (được phép hay không, số request còn lại)."""
        current = time.monotonic() if now is None else now
        window_start = current - self.window_seconds
        hits = self._hits[key]

        while hits and hits[0] <= window_start:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False, 0

        hits.append(current)
        return True, self.max_requests - len(hits)

    def reset(self) -> None:
        self._hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Chặn request vượt giới hạn, chỉ áp dụng cho các path chat."""

    _PROTECTED_PREFIXES = ("/api/v1/chat",)

    def __init__(self, app: Callable[..., object], settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings
        self.limiter = SlidingWindowRateLimiter(
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self.settings.rate_limit_enabled or not self._is_protected(request):
            return await call_next(request)

        key = client_key(request)
        allowed, remaining = self.limiter.allow(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content=error_payload(
                    "rate_limit_exceeded",
                    f"Bạn đã gửi quá {self.settings.rate_limit_requests} yêu cầu "
                    f"trong {self.settings.rate_limit_window_seconds} giây. Thử lại sau.",
                ),
                headers={"Retry-After": str(self.settings.rate_limit_window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _is_protected(self, request: Request) -> bool:
        return request.url.path.startswith(self._PROTECTED_PREFIXES)


def client_key(request: Request) -> str:
    """Khóa định danh người gọi.

    Dùng chung cho rate limit và hàng đợi (`app/services/queue/`) để hai cơ chế
    nhìn "một người dùng" giống hệt nhau.

    Ưu tiên `user_id` từ token (FR-09 đúng nghĩa "mỗi user"). Giai đoạn 1 chưa bật
    auth nên luôn lùi về IP — vẫn chặn được spam cơ bản.
    """
    user_id = get_current_user_id(request)
    if user_id is not None:
        return f"user:{user_id}"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"
