"""Fixture dùng chung — mọi test chạy với MockProvider, không cần Ollama."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        llm_provider="mock",
        cors_origins=["http://localhost:3000"],
        rate_limit_enabled=False,
        max_history_messages=10,
        log_level="WARNING",
        # Ép in-memory, KHÔNG đụng Postgres thật: pydantic vẫn đọc DATABASE_NAME từ .env
        # nếu ta không ghi đè, nên phải set None tường minh cho test hermetic.
        database_name=None,
        database_url=None,
        # JWT_SECRET cố định để token ổn định qua các lần chạy.
        jwt_secret="test-secret-cho-integration-test-du-dai-32b",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """TestClient chạy qua lifespan để provider + repository được khởi tạo."""
    with TestClient(create_app(settings)) as test_client:
        yield test_client
