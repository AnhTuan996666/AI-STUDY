"""Giao diện chung cho mọi LLM provider.

Đổi model server (Ollama -> vLLM -> API bên thứ 3) chỉ cần thêm 1 lớp con,
không đụng vào tầng API. Đáp ứng NFR-04 / NFR-06.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

from app.modules.chat.schemas import ChatMessage


@dataclass
class LLMChunk:
    """Một mẩu nội dung trong luồng streaming."""

    content: str
    done: bool = False
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass
class LLMModel:
    """Một model mà server đang phục vụ (nguồn cho `GET /models`)."""

    id: str
    name: str | None = None
    description: str | None = None
    size_bytes: int | None = None


@dataclass
class LLMResult:
    """Kết quả đầy đủ của một lượt sinh."""

    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class LLMProvider(ABC):
    """Hợp đồng mà mọi provider phải thỏa mãn."""

    name: str

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Tên model mặc định của provider."""

    @abstractmethod
    async def health(self) -> bool:
        """True nếu model server đang phục vụ được."""

    @abstractmethod
    async def list_models(self) -> list[LLMModel]:
        """Danh sách model đang có. Trả list rỗng nếu không hỏi được server."""

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResult:
        """Sinh câu trả lời đầy đủ."""

    @abstractmethod
    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]:
        """Sinh câu trả lời theo luồng."""

    # Cố ý KHÔNG @abstractmethod: provider nào không giữ tài nguyên (vd MockProvider)
    # thì dùng luôn bản mặc định rỗng này, khỏi phải viết lại.
    async def aclose(self) -> None:  # noqa: B027
        """Giải phóng tài nguyên (mặc định: không có gì)."""
