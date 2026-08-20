# model/ — Lớp model (Ollama + Python)

Mục đích: xác thực model chạy được **trước khi** ghép vào backend. Toàn bộ code ở đây
đồng bộ (sync) và tối giản để dễ chạy/debug trong terminal.

## Cấu trúc

```
model/
├── ollama_lab/          # package tái sử dụng được
│   ├── config.py        # Settings đọc từ .env
│   └── client.py        # OllamaClient: chat() + chat_stream()
├── scripts/             # script chạy tay theo từng mốc
│   ├── step0_check.py       # kiểm tra Ollama sống + list model
│   ├── step1_chat_once.py   # mốc 2: gọi model, KHÔNG streaming
│   ├── step2_chat_stream.py # mốc 3: streaming + đo TTFT
│   └── step3_chat_terminal.py # REPL nhiều lượt, nhớ ngữ cảnh
└── tests/               # pytest, dùng MockTransport, KHÔNG cần Ollama
```

## Chạy

Bật venv một lần, sau đó dùng `task <tên>` (kiểu `npm run`, cấu hình ở
`[tool.taskipy.tasks]` trong `pyproject.toml`) — giống hệt bên `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
task --list                  # xem tất cả lệnh có sẵn
```

| Lệnh | Làm gì | Cần Ollama? |
|---|---|---|
| `task ping` | Ollama sống chưa + liệt kê model đã pull (mốc 1) | ☑ |
| `task chat "câu hỏi"` | Gọi model 1 lần, chờ trả lời đầy đủ (mốc 2) | ☑ |
| `task stream "câu hỏi"` | Gọi streaming + đo TTFT (mốc 3) | ☑ |
| `task repl` | Chat nhiều lượt trong terminal, nhớ ngữ cảnh | ☑ |
| `task test` | 8 test, dùng `MockTransport` | ☐ |
| `task lint` / `fix` / `fmt` | ruff | ☐ |
| `task check` | lint + test — chạy trước khi commit | ☐ |

Bỏ trống câu hỏi thì `chat` / `stream` dùng prompt mặc định trong script.
Vẫn gọi thẳng được nếu muốn: `python scripts\step1_chat_once.py "..."`.

## Ghi chú API Ollama

| Endpoint | Dùng để |
|---|---|
| `GET /api/tags` | Liệt kê model đã pull, cũng dùng làm health check |
| `POST /api/chat` `stream=false` | Trả 1 JSON object đầy đủ |
| `POST /api/chat` `stream=true` | Trả NDJSON, mỗi dòng 1 object; dòng cuối `done=true` kèm số token |
