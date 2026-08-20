"""Lớp thử nghiệm Ollama bằng Python.

Mục đích: xác thực model chạy được (mốc 1-3) trước khi ghép vào backend.
Code ở đây cố ý giữ tối giản, đồng bộ (sync) để dễ chạy trong terminal.
"""

from ollama_lab.client import ChatChunk, ChatResult, OllamaClient, OllamaError
from ollama_lab.config import Settings, load_settings

__all__ = [
    "ChatChunk",
    "ChatResult",
    "OllamaClient",
    "OllamaError",
    "Settings",
    "load_settings",
]
