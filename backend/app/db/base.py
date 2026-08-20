"""Khai báo Base cho ORM.

Quy ước của dự án: **domain model** (dataclass) và **ORM model** nằm cùng file
`models.py` của từng module, kèm hai hàm `to_domain()` / `from_domain()`. Tầng service
chỉ làm việc với dataclass, nên đổi ORM không ảnh hưởng gì phía trên (NFR-04).

File này CHỈ khai báo `Base` và kiểu dùng chung — cố tình không import model nào, vì
model nào cũng import ngược lại `Base` (sẽ thành vòng import). Nơi gom toàn bộ model
cho Alembic là `app/db/registry.py`.

DDL tham chiếu: docs/DATABASE_SCHEMA.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

# Đặt tên ràng buộc theo khuôn: Alembic autogenerate mới sinh được lệnh DROP đúng tên,
# nếu không thì mọi migration đụng tới constraint đều phải sửa tay.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base chung cho mọi bảng."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UtcDateTime(TypeDecorator[datetime]):
    """`timestamptz` luôn đọc ra datetime **có** tzinfo=UTC.

    Vì sao cần: một số driver trả về datetime naive, so sánh với `datetime.now(UTC)`
    sẽ ném TypeError ngay giữa luồng đăng nhập. Ép kiểu ở một chỗ rẻ hơn là đi vá
    từng chỗ dùng.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=UTC)


__all__ = ["Base", "UtcDateTime"]
