# CHECKLIST TEST — 7 MỐC MVP

Đánh dấu ☑ khi bạn tự tay chạy và thấy đúng kết quả mong đợi.

---

## Mốc 1 — Test chat trên terminal

☐ **Điều kiện:** đã cài Ollama và pull model.

```powershell
ollama run qwen2.5:7b
```

| Kiểm tra | Đạt khi |
|---|---|
| Model phản hồi | Gõ "Xin chào" → có câu trả lời |
| Tiếng Việt | Trả lời tiếng Việt tự nhiên, không lẫn tiếng Trung/Anh |
| Tốc độ | Chữ hiện ra liên tục, không đứng > 10s |

Thay thế bằng Python (có nhớ ngữ cảnh nhiều lượt):

```powershell
cd model; .\.venv\Scripts\Activate.ps1; python scripts\step3_chat_terminal.py
```

---

## Mốc 2 — Script Python gọi model (KHÔNG streaming)

```powershell
cd model
.\.venv\Scripts\Activate.ps1
python scripts\step0_check.py
python scripts\step1_chat_once.py "Giải thích REST API trong 3 câu"
```

| Kiểm tra | Đạt khi |
|---|---|
| `step0_check.py` | In `[OK] Ollama đang chạy` + danh sách model, exit code 0 |
| Toàn bộ câu trả lời | Hiện một lần sau khi model xong |
| Số đo | In `latency`, `prompt tokens`, `completion tokens` |

☐ Đạt

---

## Mốc 3 — Script Python streaming

```powershell
python scripts\step2_chat_stream.py "Viết 100 từ về AI"
```

| Kiểm tra | Đạt khi |
|---|---|
| Streaming thật | Chữ hiện **dần từng đoạn**, không phải một cục |
| TTFT | `time to first token` < 5000 ms (NFR-02) |
| Số chunk | `chunks` > 10 |

☐ Đạt

---

## Mốc 4 — FastAPI `/chat` cơ bản

```powershell
.\scripts\start-backend.ps1
```

Mở http://localhost:8000/docs → thử endpoint `POST /api/v1/chat`.

| Kiểm tra | Đạt khi |
|---|---|
| Swagger | Trang `/docs` mở được, thấy 3 endpoint |
| Trả lời | Nhận JSON có `content`, `model`, `latency_ms`, `usage` |
| Validate | Gửi `{"messages": []}` → HTTP 422 |
| Health | `GET /api/v1/health` trả `status: ok`, `llm_reachable: true` |
| Lỗi rõ ràng | Tắt Ollama → HTTP 503 với thông điệp tiếng Việt |

☐ Đạt

---

## Mốc 5 — FastAPI `/chat` có streaming (SSE)

```powershell
backend\.venv\Scripts\python.exe scripts\smoke_test.py
```

| Kiểm tra | Đạt khi |
|---|---|
| Content-Type | `text/event-stream` |
| Nhiều chunk | `số chunk` > 1 (script tự fail nếu chỉ có 1) |
| Trải theo thời gian | `khoảng trải chunk` > 0 ms → dữ liệu về dần thật |
| Kết thúc đúng | Có event `done` kèm `model` + `usage` |
| Không bị buffer | Header `X-Accel-Buffering: no` |

☐ Đạt

---

## Mốc 6 — Next.js frontend UI cơ bản

```powershell
.\scripts\start-frontend.ps1
```

Mở http://localhost:3000

| Kiểm tra | Đạt khi |
|---|---|
| Trang tải được | Thấy màn hình "Bắt đầu trò chuyện" |
| Badge trạng thái | Góc trên phải hiện tên model (không phải "Mất kết nối") |
| Ô nhập | Gõ được, textarea tự giãn cao dần |
| Phím tắt | Enter gửi, Shift+Enter xuống dòng |
| Sidebar | Nút "+ Hội thoại mới" bấm được |
| Responsive | Thu nhỏ cửa sổ → sidebar ẩn, có nút ☰ |

☐ Đạt

---

## Mốc 7 — Nối frontend ↔ backend streaming thật

Yêu cầu: backend `:8000` + frontend `:3000` cùng chạy.

| Kiểm tra | Đạt khi |
|---|---|
| Gửi tin nhắn | Tin của bạn hiện bên phải ngay lập tức |
| Chấm loading | Bong bóng AI hiện 3 chấm nhấp nháy trước khi có chữ |
| Streaming | Chữ hiện **dần**, có con trỏ ▍ nhấp nháy ở cuối |
| Tự cuộn | Trang tự cuộn xuống theo nội dung mới |
| Nút Dừng | Bấm giữa chừng → ngắt ngay, giữ lại phần đã nhận |
| Markdown | Hỏi "viết hàm Python đọc CSV" → code block có nền tối, có bảng nếu hỏi bảng |
| Lưu lịch sử | F5 → hội thoại vẫn còn trong sidebar |
| Đa hội thoại | Tạo hội thoại mới → nội dung tách biệt, đổi tên/xóa được |
| Lỗi hiển thị rõ | Tắt backend rồi gửi → banner đỏ "Không kết nối được backend…" |

☐ Đạt

---

## Test tự động (chạy bất cứ lúc nào, không cần Ollama)

```powershell
.\scripts\run-tests.ps1
```

| Nhóm | Số lượng | Nội dung |
|---|---|---|
| `model/` pytest | 8 | OllamaClient: health, list model, chat, streaming, dòng NDJSON hỏng, lỗi HTTP |
| `backend/tests/unit` | 35 | ChatService, OllamaProvider, repositories, utils, security, sliding window |
| `backend/tests/integration` | 31 | Endpoint chat/stream/health, validate, CORS, rate limit qua HTTP |
| `frontend` typecheck | — | `tsc --noEmit` |
| `frontend` lint | — | ESLint (gồm rule của React Compiler) |
| `frontend` build | — | `next build` production |

Chạy riêng từng nhóm backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m pytest tests/integration -q
```
