"""Exception nghiệp vụ + handler chuyển thành HTTP response chuẩn."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Lỗi nghiệp vụ có mã HTTP kèm theo."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    retry_after_seconds: int | None = None
    """Nếu có, handler sẽ gắn header `Retry-After` để client biết khi nào thử lại."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LLMUnavailableError(AppError):
    """Không gọi được model server (Ollama chết, timeout, HTTP lỗi)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "llm_unavailable"


class RateLimitExceededError(AppError):
    """Vượt quá giới hạn số request."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_exceeded"


class QueueFullError(AppError):
    """Hàng đợi trước model server đã đầy — từ chối ngay thay vì bắt người dùng chờ vô vọng."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "queue_full"
    retry_after_seconds = 30


class QueueTimeoutError(AppError):
    """Chờ trong hàng đợi quá lâu mà chưa tới lượt."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "queue_timeout"
    retry_after_seconds = 30


def error_payload(code: str, message: str) -> dict[str, dict[str, str]]:
    """Định dạng lỗi thống nhất cho toàn bộ API."""
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký handler cho AppError và lỗi ngoài dự kiến."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError [%s] %s", exc.code, exc.message)
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Lỗi không mong đợi: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload("internal_error", "Đã có lỗi xảy ra phía máy chủ."),
        )
