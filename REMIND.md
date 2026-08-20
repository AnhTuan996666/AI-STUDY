# REMIND.md — Cài đặt & Cách chạy

> File nhắc việc. Đọc từ trên xuống, làm theo đúng thứ tự. Mỗi bước có **lệnh chạy** + **kết quả mong đợi**.

Môi trường đã kiểm tra: Windows 11, Python 3.14, Node v24, npm 11.

---

## 0. Cài Ollama (bắt buộc để dùng model thật)

Hiện tại máy **chưa có Ollama**. Backend vẫn chạy được ở chế độ `LLM_PROVIDER=mock`,
nhưng để chat với model thật thì cài như sau:

1. Tải: https://ollama.com/download/windows → chạy `OllamaSetup.exe`
2. Mở terminal mới, kiểm tra:

```powershell
ollama --version
```

3. Tải model (chọn 1, khuyến nghị `qwen2.5:7b` cho tiếng Việt):

```powershell
ollama pull qwen2.5:7b        # ~4.7 GB, cần ~8GB RAM
# hoặc nhẹ hơn nếu máy yếu:
ollama pull qwen2.5:3b        # ~1.9 GB
# hoặc:
ollama pull llama3.1:8b       # ~4.9 GB
```

4. Ollama chạy nền ở `http://localhost:11434`. Kiểm tra:

```powershell
curl http://localhost:11434/api/tags
```

**Ghi chú RAM/VRAM:** model 7B cần ~8GB RAM (CPU) hoặc ~6GB VRAM (GPU). Máy yếu → dùng 3b.

---

## 1. Setup toàn bộ project (1 lệnh)

```powershell
cd d:\AI_TOOL
.\scripts\setup.ps1
```

Script sẽ: tạo venv cho `model/` và `backend/`, cài pip deps, cài npm deps cho `frontend/`,
và copy các file `.env.example` → `.env`.

Nếu PowerShell chặn script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

<details>
<summary>Setup thủ công (nếu không dùng script)</summary>

```powershell
# model layer
cd d:\AI_TOOL\model
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
deactivate

# backend
cd d:\AI_TOOL\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
deactivate

# frontend
cd d:\AI_TOOL\frontend
npm install
copy .env.local.example .env.local
```
</details>

---

## 2. Checklist 7 mốc — chạy & test theo thứ tự

| # | Mốc | Lệnh | Trạng thái |
|---|---|---|---|
| 1 | Test chat trên terminal | `ollama run qwen2.5:7b` | ☐ chờ cài Ollama |
| 2 | Script Python gọi model (không streaming) | `python scripts/step1_chat_once.py` | ☐ chờ cài Ollama |
| 3 | Script Python streaming | `python scripts/step2_chat_stream.py` | ☐ chờ cài Ollama |
| 4 | FastAPI endpoint `/chat` cơ bản | `POST /api/v1/chat` | ☑ code xong, đã test (mock) |
| 5 | FastAPI endpoint `/chat` có streaming | `POST /api/v1/chat/stream` | ☑ code xong, đã test (mock) |
| 6 | Next.js frontend UI cơ bản | `npm run dev` | ☑ code xong, build sạch |
| 7 | Nối frontend ↔ backend streaming thật | Gõ tin nhắn trên UI | ☐ bạn tự nghiệm thu trên trình duyệt |

> Mốc 4-6 đã chạy được với `LLM_PROVIDER=mock` (backend giả lập streaming 50 chunk trong 2s).
> Mốc 1-3 cần Ollama thật. Mốc 7 cần bạn mở trình duyệt kiểm tra bằng mắt.

Chi tiết từng mốc bên dưới.

---

### ✅ Mốc 1 — Test chat trên terminal

```powershell
ollama run qwen2.5:7b
```

Gõ: `Xin chào, bạn là ai?` → model trả lời. Thoát bằng `/bye`.

**Đạt khi:** model trả lời được tiếng Việt, tốc độ chấp nhận được.

---

### ✅ Mốc 2 — Script Python gọi model (KHÔNG streaming)

```powershell
cd d:\AI_TOOL\model
.\.venv\Scripts\Activate.ps1
python scripts\step0_check.py        # kiểm tra Ollama sống + liệt kê model
python scripts\step1_chat_once.py "Giải thích REST API trong 3 câu"
```

**Đạt khi:** in ra toàn bộ câu trả lời một lần + thời gian phản hồi.

---

### ✅ Mốc 3 — Script Python streaming

```powershell
python scripts\step2_chat_stream.py "Viết 1 đoạn văn 100 từ về AI"
```

**Đạt khi:** chữ hiện ra dần từng token, có in `time to first token`.

Bonus — chat REPL nhiều lượt có nhớ ngữ cảnh:

```powershell
python scripts\step3_chat_terminal.py
```

---

### ✅ Mốc 4 — FastAPI `/chat` cơ bản

```powershell
cd d:\AI_TOOL\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Mở Swagger: http://localhost:8000/docs

Test bằng PowerShell:

```powershell
$body = @{ messages = @(@{ role = "user"; content = "Xin chào" }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri http://localhost:8000/api/v1/chat -Method Post -Body $body -ContentType "application/json"
```

**Đạt khi:** nhận JSON `{ content, model, usage, latency_ms }`.

> Chưa có Ollama? Đặt `LLM_PROVIDER=mock` trong `backend/.env` → vẫn trả lời (giả lập).

---

### ✅ Mốc 5 — FastAPI `/chat` có streaming (SSE)

```powershell
curl -N -X POST http://localhost:8000/api/v1/chat/stream `
  -H "Content-Type: application/json" `
  -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Đếm từ 1 đến 10\"}]}'
```

**Đạt khi:** thấy các dòng `data: {"type":"delta","content":"..."}` chảy ra dần, kết thúc bằng
`data: {"type":"done", ...}`.

---

### ✅ Mốc 6 — Next.js frontend UI cơ bản

```powershell
cd d:\AI_TOOL\frontend
npm run dev
```

Mở http://localhost:3000

**Đạt khi:** thấy khung chat, gõ được, có sidebar hội thoại, có nút gửi.

---

### ✅ Mốc 7 — Nối frontend ↔ backend streaming thật

Yêu cầu: backend đang chạy ở `:8000`, frontend ở `:3000`, và
`frontend/.env.local` có `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Gõ 1 tin nhắn trên UI.

**Đạt khi:** câu trả lời hiện dần từng chữ (không phải hiện 1 cục), badge trạng thái đổi
`đang soạn…` → `xong`, và bấm **Dừng** thì ngắt được giữa chừng.

---

## 2b. Cắm database (bật đăng nhập & lưu tài khoản)

Backend **chạy được ngay không cần DB** — khi đó tài khoản và cài đặt lưu tạm trong bộ
nhớ và **mất khi restart**. Để lưu thật (PostgreSQL):

1. Tạo database (PostgreSQL đã chạy sẵn ở `localhost:5432`):

```powershell
# Trong pgAdmin, hoặc bằng psql:
createdb -U postgres ai_chat
```

2. Điền vào `backend\.env`:

```ini
DATABASE_PASSWORD=<mật khẩu postgres của bạn>
DATABASE_NAME=ai_chat
JWT_SECRET=<dán chuỗi sinh ở bước 3>
```

3. Sinh `JWT_SECRET` (khoá ký phiên đăng nhập, tối thiểu 32 byte):

```powershell
cd d:\AI_TOOL\backend
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

4. Tạo bảng bằng migration:

```powershell
cd d:\AI_TOOL\backend
.\.venv\Scripts\alembic upgrade head
```

**Kết quả mong đợi**: tạo 3 bảng `users`, `user_settings`, `revoked_tokens`. Khi khởi
động backend, log **không** còn dòng cảnh báo "Chưa cấu hình database".

> Đăng nhập Google là tuỳ chọn: để trống `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
> thì nút Google báo 503 có giải thích, phần đăng nhập email/mật khẩu vẫn chạy. Muốn
> bật: tạo OAuth client ở https://console.cloud.google.com/apis/credentials, thêm
> redirect URI `http://localhost:8000/api/v1/auth/google/callback`, rồi điền 2 biến đó.

---

## 3. Chạy test tự động

```powershell
# backend
cd d:\AI_TOOL\backend
.\.venv\Scripts\Activate.ps1
pytest -v

# model layer
cd d:\AI_TOOL\model
.\.venv\Scripts\Activate.ps1
pytest -v

# frontend: typecheck + lint + build
cd d:\AI_TOOL\frontend
npm run typecheck
npm run lint
npm run build
```

Toàn bộ test **không cần Ollama** (dùng mock/fake transport).

---

## 4. Biến môi trường

### `backend/.env`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `production` |
| `LLM_PROVIDER` | `ollama` | `ollama` \| `mock` (mock để dev không cần GPU) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Tên model |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Timeout gọi model |
| `CORS_ORIGINS` | `http://localhost:3000` | Danh sách origin, ngăn cách dấu phẩy |
| `RATE_LIMIT_REQUESTS` | `20` | Số request tối đa |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | …trong bao nhiêu giây |
| `LOG_LEVEL` | `INFO` | Mức log |

### `frontend/.env.local`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | URL backend |

### `model/.env`

| Biến | Mặc định |
|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `qwen2.5:7b` |

---

## 5. Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `ollama: command not found` | Chưa cài / chưa mở terminal mới | Cài lại, mở PowerShell mới |
| Backend trả `503 LLM provider unavailable` | Ollama chưa chạy | `ollama serve` hoặc mở Ollama app; hoặc set `LLM_PROVIDER=mock` |
| FE gọi BE bị chặn CORS | Sai `CORS_ORIGINS` | Thêm `http://localhost:3000` vào `backend/.env` |
| Streaming hiện 1 cục thay vì dần | Proxy/antivirus buffer | Kiểm tra header `X-Accel-Buffering: no` còn nguyên, test lại bằng `curl -N` |
| `npm run dev` lỗi module | Chưa `npm install` | `cd frontend; npm install` |
| Model trả lời rất chậm | Chạy CPU / model quá lớn | Đổi sang `qwen2.5:3b` |
| PowerShell chặn `.ps1` | ExecutionPolicy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

---

## 6. Việc tiếp theo (chưa làm ở base này)

- [x] Auth: email/mật khẩu + Google OAuth (JWT) — FR-01, FR-02 ✅
- [x] Lưu tài khoản + cài đặt vào PostgreSQL — FR-08 ✅
- [x] Hàng đợi trước GPU (chống treo khi đông người) ✅
- [ ] Lưu **lịch sử hội thoại** vào PostgreSQL — FR-05 (hiện vẫn ở localStorage FE)
- [ ] Sidebar CRUD conversation gắn với DB — FR-06, FR-07
- [ ] Rate limit theo `user_id` thay vì IP — FR-09
- [ ] Deploy: Vercel (FE) + Render (BE) + Cloudflare Tunnel (Ollama)

Schema DB đã thiết kế sẵn tại [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

### Cấu trúc backend (chia theo chức năng)

Mỗi tính năng là một folder trong `backend/app/modules/`, người mới đọc tên folder là
biết nó làm gì:

```
app/modules/
├── auth/          đăng ký, đăng nhập, Google, JWT, thu hồi token
│   ├── router.py      địa chỉ API  (POST /auth/register, ...)
│   ├── service.py     nghiệp vụ    (kiểm mật khẩu, cấp token)
│   ├── repository.py  đọc/ghi DB   (bản Postgres + bản in-memory)
│   ├── models.py      bảng dữ liệu (users, revoked_tokens)
│   ├── schemas.py     khuôn JSON vào/ra
│   └── google.py      luồng OAuth Google
├── chat/          gửi tin nhắn, trả lời streaming
├── llm/           kết nối model server + hàng đợi GPU + danh sách model
│   ├── providers/     ollama | mock (đổi sang vLLM chỉ thêm 1 file)
│   └── queue/         hàng đợi chống treo
├── settings/      tuỳ chọn cá nhân (theme, model, temperature)
├── conversations/ lịch sử hội thoại
└── health/        kiểm tra hệ thống

app/core/    cấu hình, bảo mật (JWT + hash), rate limit, logging
app/db/      kết nối database, gom bảng cho Alembic
app/api/     ráp router + khai báo dependency (nơi chọn Postgres hay in-memory)
```

Cùng một mạch cho mọi tính năng: **router → service → repository**. Đọc một module là
suy ra được các module còn lại.
