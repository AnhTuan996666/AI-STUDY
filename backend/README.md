# backend/ — FastAPI

API chat giữa frontend và model server.

## Cấu trúc

```
backend/
├── app/
│   ├── main.py                  # Entry point: create_app(), lifespan, middleware
│   │
│   ├── api/                     # API / Router
│   │   ├── deps.py              # dependency dùng chung — nơi DUY NHẤT chọn cài đặt cụ thể
│   │   └── v1/
│   │       ├── router.py        # gom route
│   │       ├── chat.py          # POST /chat, POST /chat/stream
│   │       └── health.py        # GET /health
│   │
│   ├── services/                # Business logic — KHÔNG import fastapi
│   │   ├── chat_service.py
│   │   └── llm/                 # trừu tượng hóa model server
│   │       ├── base.py          # interface LLMProvider
│   │       ├── ollama_provider.py
│   │       ├── mock_provider.py
│   │       └── factory.py
│   │
│   ├── repositories/            # Database access
│   │   ├── base.py              # interface (service chỉ được import file này)
│   │   ├── conversation_repository.py
│   │   └── message_repository.py
│   │
│   ├── models/                  # DB Models (domain, dataclass)
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── schemas/                 # Request / Response (Pydantic)
│   │   ├── chat.py
│   │   └── health.py
│   │
│   ├── core/                    # Core configuration
│   │   ├── config.py            # Settings — nguồn sự thật duy nhất
│   │   ├── security.py          # JWT / định danh user (chưa bật)
│   │   ├── exceptions.py        # AppError + handler
│   │   ├── logging.py
│   │   └── rate_limit.py
│   │
│   ├── db/                      # Database (giữ chỗ, chưa cắm)
│   │   ├── session.py
│   │   └── base.py
│   │
│   └── utils/                   # Utilities thuần
│       └── text.py
│
├── tests/
│   ├── conftest.py              # fixture dùng chung
│   ├── unit/                    # logic thuần, không HTTP
│   └── integration/             # đi qua TestClient
│
├── alembic/                     # DB migration (giữ chỗ)
├── requirements.txt
├── pyproject.toml
├── .env / .env.example
└── README.md
```

## Quy tắc phân tầng (bất di bất dịch)

```
api/  →  services/  →  repositories/  →  db/
HTTP     nghiệp vụ     truy cập data    kết nối
             ↓
        services/llm/  →  model server
```

- `api/` chỉ nhận request, gọi service, trả response. Không tính toán nghiệp vụ.
- `services/` **không import `fastapi`** và **không import lớp repository cụ thể** —
  chỉ dùng interface ở `repositories/base.py`.
- Việc chọn cài đặt nào (provider nào, repository nào) nằm gọn trong `api/deps.py`.

## Endpoint

| Method | Path | Mô tả |
|---|---|---|
| GET | `/` | Metadata app |
| GET | `/api/v1/health` | Trạng thái app + model server |
| POST | `/api/v1/chat` | Chat, chờ trả lời đầy đủ (FR-03) |
| POST | `/api/v1/chat/stream` | Chat streaming qua SSE (FR-04) |
| GET | `/docs` | Swagger UI |

### Định dạng SSE của `/chat/stream`

```
data: {"type":"delta","content":"Xin "}

data: {"type":"delta","content":"chào"}

data: {"type":"done","model":"qwen2.5:7b","latency_ms":1840,"usage":{...}}
```

Khi lỗi giữa chừng: `data: {"type":"error","message":"..."}`.
Luồng **luôn** kết thúc bằng đúng một event `done` hoặc `error`.

## Chạy

Bật venv một lần, sau đó dùng `task <tên>` (kiểu `npm run`, cấu hình ở
`[tool.taskipy.tasks]` trong `pyproject.toml`):

```powershell
.\.venv\Scripts\Activate.ps1
task --list                  # xem tất cả lệnh có sẵn
```

| Lệnh | Làm gì |
|---|---|
| `task dev` | Chạy server dev tại `:8000`, tự reload khi sửa code |
| `task mock` | Như trên nhưng ép `LLM_PROVIDER=mock` (`.env.mock`) — không cần Ollama |
| `task test` | Chạy toàn bộ 66 test |
| `task test-u` / `task test-i` | Chỉ unit / chỉ integration |
| `task lint` | `ruff check .` |
| `task fix` | `ruff check . --fix` — tự sửa những lỗi sửa được |
| `task fmt` | `ruff format .` |
| `task check` | lint + test — chạy trước khi commit |

Vẫn gọi thẳng được nếu muốn: `uvicorn app.main:app --reload --port 8000`, `pytest -v`.

## Trạng thái các tầng

| Tầng | Trạng thái |
|---|---|
| `api/`, `services/`, `schemas/`, `core/`, `utils/` | ☑ Hoạt động đầy đủ |
| `models/`, `repositories/` | ◐ Domain model + interface + bản in-memory. Chưa nối vào luồng chat |
| `db/`, `alembic/` | ☐ Giữ chỗ, có hướng dẫn cắm DB trong từng file |
| `core/security.py` | ◐ Có sẵn khung; `get_current_user_id` trả None cho tới khi bật Supabase Auth |

## Mở rộng

| Muốn làm gì | Sửa ở đâu |
|---|---|
| Đổi model server (vLLM, API bên thứ 3) | Thêm lớp con `LLMProvider` trong `services/llm/`, đăng ký ở `factory.py` |
| Cắm PostgreSQL | Điền `db/base.py` + `db/session.py`, thêm `SqlConversationRepository`, đổi 2 dòng trong `main.py` lifespan |
| Bật auth | Điền `core/security.py`, thêm `api/v1/auth.py` |
| Thêm nhóm route mới | Tạo `api/v1/<tên>.py`, include vào `api/v1/router.py` |
