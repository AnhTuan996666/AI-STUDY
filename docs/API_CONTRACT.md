# Hợp đồng API

Frontend **đã dựng xong** các endpoint dưới đây: service gọi đúng đường dẫn, Zod validate
đúng schema, store và UI đã nối. Backend chỉ cần cài đặt đúng bản mô tả này là chạy được
ngay — **không phải sửa dòng nào ở frontend**.

Tiền tố chung: `/api/v1` (xem `API.prefix` trong `frontend/src/utils/constants.ts`).

| Endpoint | Trạng thái | Frontend gọi ở |
|---|---|---|
| `POST /chat` | ☑ đã có | `services/chat/chatService.ts` |
| `POST /chat/stream` | ☑ đã có (lưu tin qua `conversation_id`) | `services/chat/chatService.ts` |
| `GET /health` | ☑ đã có | `services/chat/chatService.ts` |
| `POST /auth/register` | ☑ đã có | `services/auth/authService.ts` |
| `POST /auth/login` | ☑ đã có | `services/auth/authService.ts` |
| `GET /auth/me` | ☑ đã có | `services/auth/authService.ts` |
| `POST /auth/logout` | ☑ đã có | `services/auth/authService.ts` |
| `GET /auth/google/authorize` | ☑ đã có | `services/auth/authService.ts` |
| `GET /auth/google/callback` | ☑ đã có | (Google gọi, không phải frontend) |
| `GET /conversations` | ☑ đã có | `services/chat/conversationService.ts` |
| `GET /conversations/{id}` | ☑ đã có | `services/chat/conversationService.ts` |
| `POST /conversations` | ☑ đã có | `services/chat/conversationService.ts` |
| `PATCH /conversations/{id}` | ☑ đã có | `services/chat/conversationService.ts` |
| `DELETE /conversations/{id}` | ☑ đã có | `services/chat/conversationService.ts` |
| `GET /models` | ☑ đã có | `services/settings/settingsService.ts` |
| `GET /settings` | ☑ đã có | `services/settings/settingsService.ts` |
| `PUT /settings` | ☑ đã có | `services/settings/settingsService.ts` |

## Quy ước chung

- Trường JSON dùng `snake_case` để khớp Pydantic (xem `docs/CODING_STANDARDS.md`).
- Lỗi trả về đúng khuôn đang dùng: `{"error": {"code": "...", "message": "..."}}`.
  `message` là **tiếng Việt, hành động được** — frontend hiện thẳng chuỗi này cho người dùng.
- Endpoint chưa cài đặt thì trả **404**. Frontend bắt riêng mã này (`isNotImplemented`)
  và lùi về phương án dự phòng thay vì hiện lỗi đỏ.
- Phiên hết hạn trả **401**; frontend tự đăng xuất và xoá dữ liệu đang hiển thị.

---

## Phiên đăng nhập: JWT bearer

Backend cấp **access token JWT** khi đăng nhập. Frontend lưu token (localStorage) và gửi
lại ở header `Authorization: Bearer <token>` cho mọi request cần đăng nhập —
`services/api.ts` tự gắn.

- Token sai / hết hạn / đã đăng xuất: **401**, frontend tự xoá phiên và về trạng thái khách.
- Đăng xuất thu hồi token phía server (bảng `revoked_tokens`), nên token cũ không dùng lại được.
- Đổi `JWT_SECRET` = vô hiệu hoá mọi token đang lưu hành.

> **CORS:** `allow_origins` là **danh sách cụ thể** lấy từ `settings.cors_origins`
> (không dùng `["*"]`). Danh sách này cũng là các origin được phép nhận token sau khi
> đăng nhập Google.

---

## Auth

### `POST /auth/register`

```jsonc
// Request
{ "email": "ban@congty.com", "password": "matkhau123", "display_name": "Nguyễn Văn A" }

// Response 201
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 604800,          // giây
  "user": { "id": "uuid", "email": "...", "display_name": "...", "avatar_url": null,
            "provider": "password", "created_at": "2026-08-20T10:00:00Z" }
}
```

Frontend đã kiểm trước khi gửi (`schemas/authSchema.ts`): email hợp lệ, mật khẩu 8–128 ký
tự, tên hiển thị 1–60 ký tự. Backend **vẫn kiểm lại** — client không đáng tin.

Email trùng: **409**, `code: "email_taken"`.

### `POST /auth/login`

Request `{ "email": ..., "password": ... }`, response giống `/auth/register`.
Sai thông tin: **401**, `code: "invalid_credentials"` (email không tồn tại cũng trả mã
này để không lộ email nào đã đăng ký).

### `GET /auth/me`

Cần token. Response là **object user trần** (không bọc `{ user }`):

```jsonc
{ "id": "uuid", "email": "...", "display_name": "...", "avatar_url": null,
  "provider": "password", "created_at": "..." }
```

Token hỏng / hết hạn / đã đăng xuất: **401**.

### `POST /auth/logout`

Cần token. Thu hồi token hiện tại phía server. Response 200 `{ "detail": "Đã đăng xuất." }`.
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

4. Backend: đổi code lấy token → lấy hồ sơ → tạo/tìm/gắn user → cấp JWT
   → 302 về redirect_uri kèm token ở query string:
     {redirect_uri}?access_token=...&token_type=bearer&expires_in=604800

5. Trang /auth/callback đọc access_token khỏi query, lưu lại, gọi GET /auth/me,
   rồi replaceState về "/" để token không nằm lại trong lịch sử trình duyệt
```

### `GET /auth/google/authorize`

Query `redirect_uri` (bắt buộc). **Phải kiểm `redirect_uri` nằm trong danh sách cho phép**
(dùng luôn `settings.cors_origins`) — không thì thành lỗ hổng open redirect.

Trả **302** sang Google.

### `GET /auth/google/callback`

Google gọi, không phải frontend. Kết thúc bằng **302** về `redirect_uri` kèm
`access_token` ở query string.

Lỗi (người dùng huỷ, state hỏng…) thì vẫn 302 về `redirect_uri` nhưng kèm
`?error=<thông điệp>` thay cho token — trang callback hiển thị chuỗi này.

> Token nằm trên URL chỉ trong đúng một lần điều hướng: trang callback đọc xong là
> `history.replaceState` về `/`, không để token lọt vào lịch sử trình duyệt.

Biến môi trường backend: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
Bỏ trống hai biến đầu = tắt Google (`/auth/google/*` trả **503** `google_oauth_disabled`).

---

## Conversations

Cần token. Tất cả đều lọc theo user đang đăng nhập.

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

Cần token. Cài đặt gắn theo tài khoản.

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

> Theme cho lần tải trang sau do **frontend** tự nhớ (localStorage `ai-chat:theme`, đọc
> trước khi vẽ để tránh chớp sáng). Backend không cần làm gì thêm cho việc này.

---

## Bảng cần thêm vào database

Chi tiết cột: xem `docs/DATABASE_SCHEMA.md`.

| Bảng | Ghi chú |
|---|---|
| `users` | ✅ đã tạo — `provider`, `google_sub` (unique, nullable), `avatar_url`; `password_hash` null với tài khoản Google |
| `revoked_tokens` | ✅ đã tạo — `jti`, `user_id`, `expires_at` (thu hồi token khi đăng xuất) |
| `user_settings` | ✅ đã tạo — 1–1 với `users`, các cột đúng như mục Settings |
| `conversations` | ✅ đã tạo — kèm `is_pinned boolean not null default false` |
| `messages` | ✅ đã tạo — role/content/token/latency, cascade theo conversation |

Năm bảng ✅ tạo bằng: `alembic upgrade head`.

---

## Những thứ frontend KHÔNG còn lưu ở trình duyệt

Toàn bộ đã chuyển sang database:

| Trước | Giờ |
|---|---|
| `localStorage['ai-chat:conversations']` | `GET/POST/PATCH/DELETE /conversations` ✅ |
| `localStorage['ai-chat:settings']` | `GET/PUT /settings` ✅ |

Frontend còn giữ ở `localStorage` đúng hai thứ nhẹ: `ai-chat:auth` (token JWT của phiên)
và `ai-chat:theme` (để không chớp sáng lúc tải trang). Khách chưa đăng nhập vẫn chat được,
nhưng hội thoại chỉ nằm trong bộ nhớ trang — tải lại là mất.
