# Hợp đồng API

Frontend **đã dựng xong** các endpoint dưới đây: service gọi đúng đường dẫn, Zod validate
đúng schema, store và UI đã nối. Backend chỉ cần cài đặt đúng bản mô tả này là chạy được
ngay — **không phải sửa dòng nào ở frontend**.

Tiền tố chung: `/api/v1` (xem `API.prefix` trong `frontend/src/utils/constants.ts`).

| Endpoint | Trạng thái | Frontend gọi ở |
|---|---|---|
| `POST /chat` | ☑ đã có | `services/chat/chatService.ts` |
| `POST /chat/stream` | ◐ đã có, **cần thêm** `conversation_id` | `services/chat/chatService.ts` |
| `GET /health` | ☑ đã có | `services/chat/chatService.ts` |
| `POST /auth/register` | ☐ **cần làm** | `services/auth/authService.ts` |
| `POST /auth/login` | ☐ **cần làm** | `services/auth/authService.ts` |
| `GET /auth/me` | ☐ **cần làm** | `services/auth/authService.ts` |
| `POST /auth/logout` | ☐ **cần làm** | `services/auth/authService.ts` |
| `GET /auth/google/authorize` | ☐ **cần làm** | `utils/authUrl.ts` |
| `GET /auth/google/callback` | ☐ **cần làm** | (Google gọi, không phải frontend) |
| `GET /conversations` | ☐ **cần làm** | `services/chat/conversationService.ts` |
| `GET /conversations/{id}` | ☐ **cần làm** | `services/chat/conversationService.ts` |
| `POST /conversations` | ☐ **cần làm** | `services/chat/conversationService.ts` |
| `PATCH /conversations/{id}` | ☐ **cần làm** | `services/chat/conversationService.ts` |
| `DELETE /conversations/{id}` | ☐ **cần làm** | `services/chat/conversationService.ts` |
| `GET /models` | ☐ **cần làm** | `services/settings/settingsService.ts` |
| `GET /settings` | ☐ **cần làm** | `services/settings/settingsService.ts` |
| `PUT /settings` | ☐ **cần làm** | `services/settings/settingsService.ts` |

## Quy ước chung

- Trường JSON dùng `snake_case` để khớp Pydantic (xem `docs/CODING_STANDARDS.md`).
- Lỗi trả về đúng khuôn đang dùng: `{"error": {"code": "...", "message": "..."}}`.
  `message` là **tiếng Việt, hành động được** — frontend hiện thẳng chuỗi này cho người dùng.
- Endpoint chưa cài đặt thì trả **404**. Frontend bắt riêng mã này (`isNotImplemented`)
  và lùi về phương án dự phòng thay vì hiện lỗi đỏ.
- Phiên hết hạn trả **401**; frontend tự đăng xuất và xoá dữ liệu đang hiển thị.

---

## Phiên đăng nhập: cookie, KHÔNG dùng JWT

Backend cấp **session id đục** (opaque, tra trong bảng `sessions`), không phải JWT.
Frontend không bao giờ cầm token: mọi request đều gửi kèm `credentials: 'include'`.

Cần **hai** cookie:

| Cookie | httpOnly | Secure | SameSite | Nội dung |
|---|---|---|---|---|
| `ai_chat_session` | ✅ | ✅ (prod) | `Lax` cùng domain, `None` khác domain | session id |
| `ai-chat-client-auth-info` | ❌ | ✅ (prod) | như trên | JSON, xem dưới |

Cookie thứ hai **không phải chứng thực** — nó chỉ để frontend vẽ đúng ngay từ khung hình
đầu tiên, khỏi phải chờ `/auth/me`. Ai cũng sửa được nó, nên backend **tuyệt đối không**
tin nó; quyền thật luôn tra từ `ai_chat_session`.

```jsonc
// Giá trị của ai-chat-client-auth-info (URL-encoded JSON)
{
  "user": { "id": "...", "email": "...", "display_name": "...", "avatar_url": null, "provider": "google" },
  "theme": "dark",              // giúp đặt data-theme trước khi trang vẽ, tránh chớp sáng
  "expires_at": 1755680000000   // mili giây
}
```

Backend phải ghi lại cookie này **mỗi khi** user hoặc theme đổi (đăng nhập, `PUT /settings`),
và xoá cả hai khi đăng xuất.

> **CORS bắt buộc:** `allow_credentials=True` kèm **danh sách origin cụ thể**.
> `allow_origins=["*"]` không dùng được với cookie — trình duyệt sẽ chặn.
> Sửa ở `backend/app/main.py`, lấy từ `settings.cors_origins`.

---

## Auth

### `POST /auth/register`

```jsonc
// Request
{ "email": "ban@congty.com", "password": "matkhau123", "display_name": "Nguyễn Văn A" }

// Response 201 — kèm Set-Cookie cho cả hai cookie
{ "user": { "id": "uuid", "email": "...", "display_name": "...", "avatar_url": null,
            "provider": "password", "created_at": "2026-08-20T10:00:00Z" } }
```

Frontend đã kiểm trước khi gửi (`schemas/authSchema.ts`): email hợp lệ, mật khẩu 8–128 ký
tự, tên hiển thị 1–60 ký tự. Backend **vẫn phải kiểm lại** — client không đáng tin.

Email trùng: **409**, `code: "email_taken"`.

### `POST /auth/login`

Request `{ "email": ..., "password": ... }`, response giống `/auth/register`.
Sai thông tin: **401**, `code: "invalid_credentials"`.

### `GET /auth/me`

Cần cookie phiên. Response `{ "user": { ... } }`. Phiên hỏng/hết hạn: **401**.

### `POST /auth/logout`

Xoá phiên trong DB và gỡ **cả hai** cookie. Response 200, body bất kỳ.
Frontend nuốt mọi lỗi ở đây vì trạng thái phía client đã dọn xong rồi.

---

## Google OAuth

Luồng chuẩn Authorization Code. Frontend **không** đụng tới token của Google.

```
1. Người dùng bấm "Tiếp tục với Google"
   → trình duyệt điều hướng cả trang tới:
     GET /api/v1/auth/google/authorize?redirect_uri=http://localhost:3000/auth/callback

2. Backend lưu redirect_uri vào state (chống CSRF), rồi 302 sang accounts.google.com

3. Google trả người dùng về:
     GET /api/v1/auth/google/callback?code=...&state=...

4. Backend: đổi code lấy token → lấy hồ sơ → tạo/tìm user → tạo session
   → Set-Cookie cả hai cookie
   → 302 về redirect_uri đã lưu trong state

5. Trang /auth/callback gọi GET /auth/me xác nhận rồi chuyển về "/"
```

### `GET /auth/google/authorize`

Query `redirect_uri` (bắt buộc). **Phải kiểm `redirect_uri` nằm trong danh sách cho phép**
(dùng luôn `settings.cors_origins`) — không thì thành lỗ hổng open redirect.

Trả **302** sang Google.

### `GET /auth/google/callback`

Google gọi, không phải frontend. Kết thúc bằng **302** về `redirect_uri`.

Lỗi thì vẫn 302 về `redirect_uri` nhưng kèm `?error=<thông điệp tiếng Việt>` —
trang callback hiển thị nguyên văn chuỗi này.

> **Không** nhét token vào URL. Cookie đã set ở bước này rồi; token trên URL sẽ lọt vào
> lịch sử trình duyệt, log máy chủ và header `Referer`.

Biến môi trường cần thêm cho backend: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_REDIRECT_URI`.

---

## Conversations

Cần cookie phiên. Tất cả đều lọc theo user đang đăng nhập.

### `GET /conversations`

Bản **rút gọn**, không kèm tin nhắn — sidebar chỉ cần tiêu đề.

```jsonc
{
  "conversations": [
    { "id": "uuid", "title": "Giải thích REST API",
      "created_at": "2026-08-20T10:00:00Z", "updated_at": "2026-08-20T10:05:00Z",
      "is_pinned": false, "message_count": 4 }
  ]
}
```

Sắp xếp `updated_at` giảm dần. Frontend tự tách nhóm ghim / gần đây.

### `GET /conversations/{id}`

Bản **đầy đủ**. Frontend gọi lần đầu người dùng bấm vào một hội thoại.

```jsonc
{
  "conversation": {
    "id": "uuid", "title": "...", "created_at": "...", "updated_at": "...",
    "is_pinned": false, "message_count": 4,
    "messages": [
      { "id": "uuid", "role": "user", "content": "...", "created_at": "..." },
      { "id": "uuid", "role": "assistant", "content": "...", "created_at": "..." }
    ]
  }
}
```

Không phải của mình: **404** (không dùng 403 — đừng để lộ là id đó có tồn tại).

### `POST /conversations`

Request `{ "title": "..." }`, response `{ "conversation": {...} }` với `messages: []`.

Frontend gọi **trước** khi gửi tin đầu tiên, để có id truyền vào `conversation_id`.

### `PATCH /conversations/{id}`

Request `{ "title"?: "...", "is_pinned"?: true }` — gửi trường nào sửa trường đó.
Response `{ "conversation": {...} }`.

### `DELETE /conversations/{id}`

Response 200 hoặc 204, body bất kỳ.

---

## Lưu tin nhắn: `conversation_id` trong `/chat/stream`

Frontend đã gửi kèm trường này. Backend cần:

```jsonc
// POST /chat/stream
{ "messages": [...], "model": null, "temperature": 0.7, "conversation_id": "uuid" }
```

- Có `conversation_id` → **lưu tin của user ngay khi nhận**, lưu câu trả lời khi stream
  xong. Nhờ vậy không cần thêm endpoint ghi tin nhắn riêng.
- `null` hoặc thiếu → không lưu gì (khách chưa đăng nhập).
- `conversation_id` không thuộc user đang đăng nhập → **404**.
- Người dùng bấm Dừng giữa chừng → vẫn lưu phần đã sinh được.

---

## Models

### `GET /models`

Không cần đăng nhập.

```jsonc
{
  "models": [
    { "id": "qwen2.5:7b", "name": "Qwen 2.5 7B",
      "description": "Cân bằng tốc độ và chất lượng",
      "size_bytes": 4680000000, "is_default": true }
  ]
}
```

Chỉ `id` là bắt buộc. Nguồn gợi ý: gọi `GET /api/tags` của Ollama rồi ánh xạ sang khuôn trên.

Chưa có endpoint này thì bộ chọn model ở header không mở menu, chỉ hiện tên model đang
chạy lấy từ `/health`.

---

## Settings

Cần cookie phiên. Cài đặt gắn theo tài khoản.

### `GET /settings`

```jsonc
{
  "settings": {
    "theme": "system",          // "system" | "light" | "dark"
    "model": null,              // null = dùng model mặc định của backend
    "temperature": 0.7,         // 0–2
    "send_on_enter": true,
    "show_suggestions": true
  }
}
```

Chưa có bản ghi thì trả mặc định như trên, **không** trả 404.

### `PUT /settings`

Request `{ "settings": { ...y như trên... } }`, response giống `GET /settings`.

> Khi `theme` đổi, backend **phải ghi lại** cookie `ai-chat-client-auth-info` với theme
> mới. Không làm thì lần tải trang sau sẽ chớp sáng trước khi chuyển sang tối.

---

## Bảng cần thêm vào database

Chi tiết cột: xem `docs/DATABASE_SCHEMA.md`.

| Bảng | Ghi chú |
|---|---|
| `users` | thêm `provider`, `google_sub` (unique, nullable), `avatar_url`; `password_hash` cho phép null với tài khoản Google |
| `sessions` | `id` (session id đục), `user_id`, `expires_at`, `created_at` |
| `conversations` | thêm `is_pinned boolean not null default false` |
| `messages` | đã có trong thiết kế |
| `user_settings` | 1–1 với `users`, các cột đúng như mục Settings |

---

## Những thứ frontend KHÔNG còn lưu ở trình duyệt

Toàn bộ đã chuyển sang database:

| Trước | Giờ |
|---|---|
| `localStorage['ai-chat:conversations']` | `GET/POST/PATCH/DELETE /conversations` |
| `localStorage['ai-chat:settings']` | `GET/PUT /settings` |
| `localStorage['ai-chat:auth']` | cookie `ai_chat_session` (httpOnly) |

Khách chưa đăng nhập vẫn chat được, nhưng hội thoại chỉ nằm trong bộ nhớ trang — tải lại
là mất. Không có đường nào ghi xuống `localStorage` nữa.
