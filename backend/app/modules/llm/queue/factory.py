"""Chọn bản hàng đợi dựa trên cấu hình."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.llm.queue.base import RequestQueue
from app.modules.llm.queue.local import LocalRequestQueue


def create_queue(settings: Settings) -> RequestQueue:
    """Dựng hàng đợi tương ứng với `settings.queue_backend`.

    Khi cần chạy nhiều instance (hoặc nhiều uvicorn worker) trên cùng một GPU,
    thêm `RedisRequestQueue` rồi rẽ nhánh ở đây — phần còn lại của app không đổi.
    """
    return LocalRequestQueue(
        max_concurrent=settings.llm_max_concurrent,
        max_queue=settings.llm_max_queue,
        wait_timeout_seconds=settings.llm_queue_timeout_seconds,
    )
