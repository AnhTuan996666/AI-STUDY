# CHUẨN CODE (CODING STANDARDS)

Áp dụng cho cả 3 layer. Mục tiêu: NFR-06 — code dễ đọc, dễ thay model/API sau này.

---

## 0. Nguyên tắc chung (cả BE và FE)

| Nguyên tắc | Ý nghĩa |
|---|---|
| Một file = một trách nhiệm | Không nhét service + route + schema chung một chỗ |
| Cấu hình tập trung | Mọi hằng số môi trường đi qua `core/config.py` (BE) / `utils/constants.ts` (FE), không rải `os.getenv` / `process.env` khắp nơi |
| Không có magic string | Đặt hằng số ở đầu file, viết HOA |
| Comment giải thích *tại sao*, không phải *cái gì* | Code đã nói *cái gì* rồi |
| Comment ngắn | Một dòng tiếng Anh là đủ. Dài hơn nghĩa là code cần tách nhỏ, hoặc phần giải thích thuộc về `docs/` |
| Ngôn ngữ | **Comment: tiếng Anh, gói gọn 1 dòng.** Thông điệp lỗi & text hiển thị cho người dùng: tiếng Việt. Tên biến/hàm/class: tiếng Anh |
| Độ dài comment | Một dòng. Cần giải thích dài hơn thì viết vào `docs/`, đừng nhồi vào file code |
| Thông điệp lỗi phải hành động được | "Không kết nối được Ollama. Kiểm tra Ollama đã chạy chưa." — không phải "Error 500" |
| Không log nội dung chat | NFR-03. Chỉ log độ dài, số token, độ trễ |

### Quy ước đặt tên

| Loại | Quy ước | Ví dụ |
|---|---|---|
| File Python | `snake_case.py` | `chat_service.py` |
| Class Python | `PascalCase` | `OllamaProvider` |
| Hàm/biến Python | `snake_case` | `latency_ms`, `create_provider` |
| Hàm private Python | tiền tố `_` | `_parse_line` |
| Thư mục component React | `PascalCase/` chứa `index.tsx` | `components/common/Button/index.tsx` |
| File service/hook/util TS | `camelCase.ts` | `chatService.ts`, `useChat.ts`, `format.ts` |
| Redux slice | `<miền>Slice.ts` | `chatSlice.ts`, `authSlice.ts` |
| Zod schema | `<miền>Schema.ts` | `chatSchema.ts` |
| Hook React | tiền tố `use` | `useChat`, `useHealth` |
| Type/Interface TS | `PascalCase` | `ChatMessage` |
| Redux action | sự việc đã xảy ra | `messageSent`, `streamEnded` |
| Biến môi trường | `SCREAMING_SNAKE_CASE` | `OLLAMA_BASE_URL` |
| Trường JSON qua API | `snake_case` | `latency_ms`, `prompt_tokens` |

> **Lưu ý:** JSON dùng `snake_case` để khớp Python; TypeScript nhận đúng tên đó trong
> `types/chat.ts` thay vì đổi sang camelCase — tránh một lớp map thừa và tránh sai sót.

---

## 1. Backend (Python / FastAPI)

### 1.1. Cấu trúc thư mục (bắt buộc)

```
backend/
├── app/
│   ├── main.py              # Entry point — KHÔNG chứa logic nghiệp vụ
│   ├── api/                 # API / Router
│   │   ├── deps.py          # dependency dùng chung
│   │   └── v1/              # mỗi file = một nhóm route (chat.py, health.py, auth.py…)
│   ├── services/            # Business logic — KHÔNG import fastapi
│   ├── repositories/        # Database access
│   ├── models/              # DB Models (domain)
│   ├── schemas/             # Request / Response (Pydantic)
│   ├── core/                # config, security, exceptions, logging, rate_limit
│   ├── db/                  # session, base
│   └── utils/               # hàm thuần
├── tests/
│   ├── unit/                # logic thuần, không HTTP
│   └── integration/         # đi qua TestClient
├── alembic/                 # DB migration
├── requirements.txt
├── .env / .env.example
└── README.md
```

**Quy ước đặt tên file theo tầng** — mỗi miền dữ liệu có bộ file cùng tên:

| Tầng | Mẫu tên | Ví dụ |
|---|---|---|
| `api/v1/` | `<miền>.py` | `chat.py`, `auth.py`, `users.py` |
| `services/` | `<miền>_service.py` | `chat_service.py`, `auth_service.py` |
| `repositories/` | `<miền>_repository.py` | `conversation_repository.py` |
| `models/` | `<thực thể>.py` (số ít) | `conversation.py`, `message.py` |
| `schemas/` | `<miền>.py` | `chat.py`, `health.py` |

### 1.2. Phân tầng — quy tắc bất di bất dịch

```
api/  →  services/  →  repositories/  →  db/
HTTP     nghiệp vụ     truy cập data    kết nối
             ↓
        services/llm/  →  model server
```

| Tầng | ĐƯỢC import | KHÔNG được import |
|---|---|---|
| `api/` | services, schemas, core | repositories (đi vòng qua service) |
| `services/` | repositories/base, models, core, utils | `fastapi`, lớp repository cụ thể |
| `repositories/` | models, db | services, api, schemas |
| `models/`, `utils/` | (gần như không gì) | mọi tầng trên |

- `api/` chỉ nhận request, gọi service, trả response. Không tính toán nghiệp vụ.
- `services/` **không được import `fastapi`**. Nhờ vậy test được mà không cần HTTP,
  và sau này tái dùng cho worker/CLI.
- `services/` chỉ biết **interface** ở `repositories/base.py`. Việc chọn cài đặt cụ thể
  (in-memory hay SQL) nằm gọn ở `api/deps.py` — đây là nơi duy nhất được phép biết.
- Đổi model server → chỉ thêm lớp con `LLMProvider`, không sửa tầng trên.

### 1.3. Quy ước bắt buộc

```python
from __future__ import annotations   # đầu mọi module

def chat(...) -> ChatResponse:        # type hint đầy đủ cho public function
    """Mô tả một dòng bằng tiếng Việt."""
```

- **Async xuyên suốt**: mọi I/O trong backend dùng `async`. Không gọi hàm blocking
  trong route (sẽ chặn cả event loop, phá streaming).
- **Exception**: ném `AppError` (hoặc lớp con) — handler ở `core/exceptions.py` tự đổi
  thành HTTP response. Không `raise HTTPException` rải rác.
- **Định dạng lỗi thống nhất**:
  ```json
  { "error": { "code": "llm_unavailable", "message": "..." } }
  ```
- **Dependency injection** qua `Annotated[X, Depends(...)]` trong `api/deps.py`,
  không tạo client mới trong từng route.

### 1.4. Định dạng & kiểm tra

```powershell
ruff check .        # lint
ruff format .       # format (line-length 100)
pytest -v           # test
```

Cấu hình trong `pyproject.toml`: `line-length = 100`, rule set `E,F,I,UP,B,SIM,ANN`.

### 1.5. Test

- Mỗi endpoint có ít nhất: 1 case thành công + 1 case validate lỗi.
- **Không test nào được phụ thuộc Ollama thật**: dùng `MockProvider` hoặc
  `httpx.MockTransport`.
- Tên test mô tả hành vi: `test_chat_returns_429_after_limit`, không phải `test_chat_2`.

---

## 2. Frontend (TypeScript / Next.js)

### 2.1. Cấu trúc thư mục (bắt buộc)

```
frontend/src/
├── app/                 # route App Router + layout + globals.css
├── components/
│   ├── common/          # Button/, Input/, Modal/, Table/… dùng lại được
│   ├── layout/          # Header/, Sidebar/, Footer/
│   └── <miền>/          # component gắn nghiệp vụ: chat/, users/, orders/
├── services/
│   ├── api.ts           # fetch + ApiError + Zod + SSE — dùng chung
│   └── <miền>/<miền>Service.ts
├── store/
│   ├── index.ts         # configureStore + typed hooks
│   └── <miền>/<miền>Slice.ts
├── hooks/<miền>/use*.ts
├── types/<miền>.ts      # kiểu, suy ra từ Zod bằng z.infer
├── schemas/<miền>Schema.ts  # validate dữ liệu qua biên
├── utils/               # constants.ts, format.ts, validation.ts, storage.ts
└── providers/           # StoreProvider.tsx…
```

**Quy ước component:** mỗi component là **một thư mục** có `index.tsx`:
`components/common/Button/index.tsx`. Component cần tách nhiều file thì đặt thêm file
cùng tên bên trong (`ChatContainer/ChatContainer.tsx`) và để `index.tsx` làm cửa ngõ.

### 2.2. Phân tầng

```
components/  →  hooks/  →  store/  →  services/
  hiển thị      binding    state      HTTP
```

| Tầng | ĐƯỢC import | KHÔNG được import |
|---|---|---|
| `components/` | hooks, components khác, types, utils | services, store (kể cả `useSelector`) |
| `components/common/` | types, utils | services, store, hooks nghiệp vụ |
| `hooks/` | store, types | services (đi vòng qua thunk) |
| `store/` | services, schemas, types, utils | React, component |
| `services/` | schemas, types, utils | store, React |

- Component **không gọi `fetch` trực tiếp** và **không `useSelector`/`useDispatch` trực
  tiếp** — chỉ dùng hook. Đổi cấu trúc store về sau không phải sửa component.
- Đổi nguồn dữ liệu (localStorage → Supabase) chỉ sửa `services/` + `utils/storage.ts`.

### 2.3. Redux Toolkit

- Reducer phải **thuần**: mọi thứ không xác định (id ngẫu nhiên, `Date.now()`, lời gọi
  mạng) sinh ở thunk rồi truyền vào qua payload. Không gọi `createId()` trong reducer.
- Không nhét giá trị không serialize được vào store (`AbortController`, `Promise`,
  class instance) — giữ ở biến module cạnh slice, như `activeController` trong `chatSlice`.
- Đặt tên action theo **sự việc đã xảy ra**, không phải câu lệnh: `messageSent`,
  `streamEnded` — không phải `setMessage`, `updateStatus`.
- Mỗi miền một slice, đăng ký trong `store/index.ts`.

### 2.4. Zod — validate ở biên

Bắt buộc validate mọi dữ liệu **không do mình tạo ra**: response backend, dữ liệu cũ
trong localStorage, query param. TypeScript chỉ kiểm tra lúc biên dịch, không cứu được
lúc chạy.

- Schema đặt ở `schemas/<miền>Schema.ts`.
- Kiểu suy ra từ schema bằng `z.infer` (`types/<miền>.ts`) — **không khai kiểu thủ công
  song song với schema**, sẽ lệch nhau.
- Dùng `safeParse`, không dùng `parse` — lỗi phải thành thông điệp tiếng Việt cho người
  dùng, không phải exception thô.

### 2.5. Quy ước bắt buộc

- `strict: true`, **không dùng `any`**. Dữ liệu ngoài (JSON) khai kiểu `unknown` rồi thu hẹp.
- `'use client'` chỉ đặt ở file thực sự cần tương tác. Mặc định là Server Component.
- Props khai bằng `interface XxxProps`, đặt ngay trên component.
- Import theo thứ tự: thư viện ngoài → alias `@/` → kiểu (`import type`).
- Dùng alias `@/` thay cho `../../..`.
- Mọi nút/icon không có nhãn chữ phải có `aria-label`.
- Text hiển thị cho người dùng: tiếng Việt, viết trực tiếp trong JSX (chưa i18n ở MVP).

### 2.6. Style (Tailwind v4)

- Màu lấy từ token trong `@theme` của `globals.css` (`bg-surface`, `text-text-muted`,
  `border-border-subtle`…). **Không hardcode mã hex trong class.**
- Class dài, có điều kiện → gom bằng mảng:
  ```tsx
  className={['rounded-lg px-3 py-2', isActive ? 'bg-accent-soft' : 'hover:bg-surface-hover'].join(' ')}
  ```
- CSS thuần chỉ dùng cho thứ Tailwind không lo được (định dạng markdown, keyframes).

### 2.7. Kiểm tra

```powershell
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm run build       # next build
```

Cả ba phải sạch trước khi commit.

---

## 3. Model layer (Python thuần)

- Cố ý **đồng bộ (sync)**, không async: mục đích là chạy tay trong terminal cho dễ debug.
- `ollama_lab/` là package tái dùng được; `scripts/` là các bước chạy tay, đặt tên
  `stepN_<việc>.py` theo đúng thứ tự mốc trong REMIND.md.
- Mỗi script trả **exit code**: `0` = đạt, `1` = lỗi → dùng được trong CI sau này.
- Script in ra số đo (TTFT, tổng thời gian, số chunk) chứ không chỉ in text — để so sánh
  chất lượng giữa các model.

---

## 4. Git & commit

Dùng Conventional Commits:

```
feat(backend): thêm endpoint /chat/stream
fix(frontend): sửa lỗi mất chunk khi SSE bị cắt giữa frame
docs: cập nhật REMIND.md mục cài Ollama
refactor(model): tách OllamaClient khỏi script
test(backend): thêm test rate limit
chore: nới version pin cho Python 3.14
```

Scope dùng đúng tên folder: `backend` · `frontend` · `model` · `docs`.

**Không commit:** `.env`, `.env.local`, `.venv/`, `node_modules/`, `.next/`.

---

## 5. Checklist trước khi commit

- [ ] `cd backend; pytest` xanh
- [ ] `cd model; pytest` xanh
- [ ] `cd frontend; npm run typecheck && npm run lint && npm run build` xanh
- [ ] Không có `console.log` / `print` debug sót lại
- [ ] Không có secret/URL nội bộ hardcode trong code
- [ ] Đã cập nhật `.env.example` nếu thêm biến môi trường mới
