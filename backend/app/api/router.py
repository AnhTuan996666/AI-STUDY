"""Gom router của mọi module lại thành một cây API.

Thêm module mới = thêm đúng 2 dòng ở đây (import + include_router).
Tiền tố `/api/v1` do `app/main.py` gắn, không lặp lại ở từng module.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.health.router import router as health_router
from app.modules.llm.router import router as llm_router
from app.modules.settings.router import router as settings_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(llm_router)
api_router.include_router(settings_router)
