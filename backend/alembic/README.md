# alembic/ — DB migration

**Trạng thái: giữ chỗ.** Dự án giai đoạn 1 chưa cắm database nên chưa có migration nào.

## Khi cắm DB, làm theo thứ tự

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install "sqlalchemy[asyncio]>=2.0" asyncpg alembic
pip freeze > requirements.lock.txt

alembic init -t async alembic      # sinh alembic.ini + alembic/env.py
```

Sau đó sửa 3 chỗ:

1. **`alembic.ini`** — bỏ dòng `sqlalchemy.url`, để `env.py` đọc từ `Settings`.
2. **`alembic/env.py`**:
   ```python
   from app.core.config import get_settings
   from app.db.base import Base

   config.set_main_option("sqlalchemy.url", get_settings().database_url)
   target_metadata = Base.metadata
   ```
3. **`app/db/base.py`** — import mọi ORM model để `--autogenerate` nhìn thấy.

Rồi sinh migration đầu tiên:

```powershell
alembic revision --autogenerate -m "tao bang conversations va messages"
alembic upgrade head
```

## Quy ước

| Việc | Lệnh |
|---|---|
| Tạo migration mới | `alembic revision --autogenerate -m "mo ta ngan"` |
| Chạy lên bản mới nhất | `alembic upgrade head` |
| Lùi 1 bản | `alembic downgrade -1` |
| Xem lịch sử | `alembic history --verbose` |

- Tên revision viết tiếng Việt không dấu, mô tả hành động: `them cot model vao conversations`.
- **Luôn đọc lại file migration do autogenerate sinh ra** trước khi chạy — Alembic thường
  bỏ sót đổi tên cột (nó hiểu nhầm thành drop + add, gây mất dữ liệu).
- Phần RLS policy (xem docs/DATABASE_SCHEMA.md mục 3) autogenerate **không** sinh được,
  phải viết tay bằng `op.execute(...)`.

DDL đầy đủ đã có sẵn tại [../../docs/DATABASE_SCHEMA.md](../../docs/DATABASE_SCHEMA.md).
