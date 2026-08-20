"""Chọn provider dựa trên cấu hình."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.providers.mock import MockProvider
from app.modules.llm.providers.ollama import OllamaProvider


def create_provider(settings: Settings) -> LLMProvider:
    """Dựng provider tương ứng với `settings.llm_provider`."""
    if settings.llm_provider == "mock":
        return MockProvider()

    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
