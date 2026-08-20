"""Cấu hình ứng dụng — nguồn sự thật duy nhất, đọc từ .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Toàn bộ biến môi trường của backend."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI Chat API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # LLM provider
    llm_provider: Literal["ollama", "mock"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 120.0

    # Hàng đợi trước model server (xem app/services/queue/)
    queue_backend: Literal["local"] = "local"
    llm_max_concurrent: int = Field(
        default=2,
        ge=1,
        description="Số lượt sinh chạy song song. Đặt bằng OLLAMA_NUM_PARALLEL.",
    )
    llm_max_queue: int = Field(
        default=32,
        ge=0,
        description="Sức chứa hàng đợi; vượt quá thì trả 503 queue_full ngay.",
    )
    llm_queue_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Chờ trong hàng đợi quá lâu thì bỏ cuộc, trả 503 queue_timeout.",
    )

    # Chat
    system_prompt: str = "Bạn là trợ lý AI hữu ích, trả lời ngắn gọn, chính xác bằng tiếng Việt."
    max_history_messages: int = Field(default=20, ge=1, le=200)

    # Database (PostgreSQL). Khai từng phần cho dễ đọc; `DATABASE_URL` nếu có sẽ
    # ghi đè tất cả — tiện khi deploy vì Render/Railway/Supabase đều phát 1 chuỗi sẵn.
    #
    # Đặt DATABASE_NAME (hoặc DATABASE_URL) = bật DB. Bỏ trống cả hai thì app chạy
    # bằng repository in-memory: tài khoản và cài đặt mất sạch mỗi lần restart, chỉ
    # hợp để dev/test.
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = ""
    database_name: str | None = None
    database_url: str | None = Field(
        default=None,
        description="Ghi đè 5 biến trên. Dạng: postgresql+psycopg://user:pass@host:5432/db",
    )
    db_echo: bool = False

    # JWT (FR-01, FR-02)
    jwt_secret: str | None = Field(
        default=None,
        description="Khóa ký token. Bắt buộc khi APP_ENV=production.",
    )
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = Field(default=604_800, ge=60)  # 7 ngày

    # Google OAuth (FR-02). Bỏ trống -> endpoint /auth/google/* trả 503 có giải thích.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
        description="Phải khớp TUYỆT ĐỐI với Authorized redirect URI khai ở Google Console.",
    )

    # CORS — NoDecode để pydantic-settings không cố parse JSON, ta tự tách dấu phẩy.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Rate limit
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=20, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Cho phép khai báo dạng chuỗi ngăn cách dấu phẩy trong .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _require_secrets_in_production(self) -> Settings:
        """Chặn ngay lúc khởi động thay vì để lộ cấu hình nguy hiểm ra Internet."""
        if self.app_env != "production":
            return self

        missing = [
            name
            for name, value in (
                ("DATABASE_NAME (hoặc DATABASE_URL)", self.database_name or self.database_url),
                ("JWT_SECRET", self.jwt_secret),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Thiếu biến bắt buộc khi APP_ENV=production: {', '.join(missing)}.")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def has_database(self) -> bool:
        """False -> mọi thứ chạy in-memory, mất dữ liệu khi restart."""
        return bool(self.database_url or self.database_name)

    @property
    def sqlalchemy_url(self) -> str | None:
        """Ghép 5 biến rời thành chuỗi kết nối; None khi chưa bật DB.

        `postgresql+psycopg` = PostgreSQL qua driver psycopg v3 ở chế độ async.
        """
        if self.database_url:
            return self.database_url
        if not self.database_name:
            return None

        password = f":{quote_plus(self.database_password)}" if self.database_password else ""
        return (
            f"postgresql+psycopg://{quote_plus(self.database_user)}{password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def has_google_oauth(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    """Settings dạng singleton (cache) — dùng làm FastAPI dependency."""
    return Settings()
