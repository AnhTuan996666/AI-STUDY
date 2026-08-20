"""Endpoint kiểm tra sức khỏe hệ thống."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ProviderDep, QueueDep, SettingsDep
from app.modules.health.schemas import HealthResponse, QueueStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Kiểm tra hệ thống")
async def health(
    provider: ProviderDep,
    queue: QueueDep,
    settings: SettingsDep,
) -> HealthResponse:
    """Trả trạng thái app + khả năng kết nối tới model server + tải hàng đợi.

    `degraded` nghĩa là API sống nhưng model server không phản hồi.
    """
    reachable = await provider.health()
    stats = queue.stats()

    return HealthResponse(
        status="ok" if reachable else "degraded",
        app_version=settings.app_version,
        llm_provider=provider.name,
        llm_reachable=reachable,
        model=provider.default_model,
        queue=QueueStatus(
            running=stats.running,
            waiting=stats.waiting,
            max_concurrent=stats.max_concurrent,
            max_queue=stats.max_queue,
            average_duration_ms=stats.average_duration_ms,
        ),
    )
