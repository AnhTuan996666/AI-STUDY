"""Nơi gom toàn bộ ORM model để Alembic nhìn thấy đầy đủ metadata.

Thêm bảng mới = thêm một dòng import ở đây. Quên dòng đó thì `alembic revision
--autogenerate` sẽ lặng lẽ sinh ra lệnh DROP bảng — nên đây là file phải nhớ.

Không import file này từ code chạy thật; nó chỉ dành cho Alembic.
"""

from __future__ import annotations

from app.db.base import Base
from app.modules.auth.models import RevokedTokenORM, UserORM
from app.modules.conversations.models import ConversationORM, MessageORM
from app.modules.settings.models import UserSettingsORM

target_metadata = Base.metadata

__all__ = [
    "Base",
    "ConversationORM",
    "MessageORM",
    "RevokedTokenORM",
    "UserORM",
    "UserSettingsORM",
    "target_metadata",
]
