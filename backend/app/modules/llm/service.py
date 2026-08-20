"""Nghiệp vụ danh sách model (GET /models).

Nguồn dữ liệu là chính provider đang chạy, nên đổi Ollama sang vLLM không phải sửa gì
ở đây — chỉ cần bản provider mới cài đặt `list_models()`.
"""

from __future__ import annotations

from app.core.config import Settings
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.schemas import ModelInfo


class ModelService:
    """Gom danh sách model và đánh dấu model mặc định."""

    def __init__(self, provider: LLMProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings

    async def list_models(self) -> list[ModelInfo]:
        default_id = self._provider.default_model
        available = await self._provider.list_models()

        models = [
            ModelInfo(
                id=model.id,
                name=model.name or model.id,
                description=model.description,
                size_bytes=model.size_bytes,
                is_default=model.id == default_id,
            )
            for model in available
        ]

        # Model mặc định phải luôn chọn được, kể cả khi server không liệt kê nó ra
        # (Ollama chết, hoặc model chưa `pull` về nhưng đã cấu hình).
        if not any(model.is_default for model in models):
            models.insert(0, ModelInfo(id=default_id, name=default_id, is_default=True))

        return models
