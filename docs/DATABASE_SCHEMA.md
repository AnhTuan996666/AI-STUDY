# THIẾT KẾ DATABASE (Supabase / PostgreSQL)

Phục vụ FR-01, FR-02, FR-05, FR-06, FR-07, FR-09.
**Chưa triển khai** — base hiện tại lưu hội thoại ở `localStorage` phía trình duyệt.
File này là bản thiết kế để bước tiếp theo cắm vào.

---

## 1. Sơ đồ quan hệ

```
auth.users (Supabase quản lý)
    │ 1
    │
    │ n
conversations
    │ 1
    │
    │ n
messages
```

| Bảng | Vai trò |
|---|---|
| `auth.users` | Supabase Auth tự tạo & quản lý. Không tự sửa. |
| `profiles` | Dữ liệu bổ sung của user (tên hiển thị, hạn mức) |
| `conversations` | Một cuộc trò chuyện |
| `messages` | Từng tin nhắn trong cuộc trò chuyện |
| `usage_logs` | Ghi nhận usage để theo dõi chi phí (FR-09, mục rủi ro #2) |

---

## 2. DDL

```sql
-- ============ profiles ============
-- Mở rộng auth.users. Supabase khuyến nghị không thêm cột vào auth.users.
create table public.profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  display_name  text,
  avatar_url    text,
  daily_quota   integer not null default 200,   -- số tin nhắn/ngày
  created_at    timestamptz not null default now()
);

-- Tự tạo profile khi có user mới
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ============ conversations ============
create table public.conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  title       text not null default 'Hội thoại mới',
  model       text,                                  -- model dùng cho hội thoại này
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Sidebar luôn sắp xếp theo lần cập nhật gần nhất của chính user đó (FR-06)
create index conversations_user_updated_idx
  on public.conversations (user_id, updated_at desc);


-- ============ messages ============
create type public.message_role as enum ('system', 'user', 'assistant');

create table public.messages (
  id                uuid primary key default gen_random_uuid(),
  conversation_id   uuid not null references public.conversations (id) on delete cascade,
  role              public.message_role not null,
  content           text not null,
  -- số đo phục vụ NFR-02 và theo dõi chi phí; null với tin của user
  prompt_tokens     integer,
  completion_tokens integer,
  latency_ms        integer,
  created_at        timestamptz not null default now()
);

-- Tải lịch sử một hội thoại theo đúng thứ tự (FR-05)
create index messages_conversation_created_idx
  on public.messages (conversation_id, created_at);


-- ============ usage_logs ============
-- Tách khỏi messages để xóa hội thoại vẫn giữ được số liệu usage.
create table public.usage_logs (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users (id) on delete cascade,
  model             text not null,
  prompt_tokens     integer not null default 0,
  completion_tokens integer not null default 0,
  latency_ms        integer,
  created_at        timestamptz not null default now()
);

create index usage_logs_user_created_idx
  on public.usage_logs (user_id, created_at desc);


-- ============ trigger cập nhật updated_at ============
create or replace function public.touch_conversation()
returns trigger language plpgsql as $$
begin
  update public.conversations
     set updated_at = now()
   where id = new.conversation_id;
  return new;
end;
$$;

create trigger messages_touch_conversation
  after insert on public.messages
  for each row execute function public.touch_conversation();
```

---

## 3. Row Level Security (NFR-03)

Bắt buộc bật RLS trên mọi bảng — nếu không, bất kỳ ai có anon key đều đọc được toàn bộ dữ liệu.

```sql
alter table public.profiles      enable row level security;
alter table public.conversations enable row level security;
alter table public.messages      enable row level security;
alter table public.usage_logs    enable row level security;

-- profiles: chỉ chính chủ
create policy "profiles_self" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

-- conversations: chỉ chủ sở hữu
create policy "conversations_owner" on public.conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- messages: gián tiếp qua conversation
create policy "messages_owner" on public.messages
  for all using (
    exists (
      select 1 from public.conversations c
       where c.id = messages.conversation_id
         and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.conversations c
       where c.id = messages.conversation_id
         and c.user_id = auth.uid()
    )
  );

-- usage_logs: user chỉ đọc của mình; ghi do backend (service role) thực hiện
create policy "usage_logs_read_self" on public.usage_logs
  for select using (auth.uid() = user_id);
```

---

## 4. Truy vấn hay dùng

```sql
-- Sidebar: danh sách hội thoại (FR-06)
select id, title, updated_at
  from conversations
 where user_id = $1
 order by updated_at desc
 limit 50;

-- Mở lại một hội thoại (FR-05)
select role, content, created_at
  from messages
 where conversation_id = $1
 order by created_at
 limit 200;

-- Rate limit theo user thay vì IP (FR-09)
select count(*)
  from usage_logs
 where user_id = $1
   and created_at > now() - interval '1 minute';

-- Theo dõi chi phí theo ngày (rủi ro #2)
select date_trunc('day', created_at) as ngay,
       count(*)                      as so_luot,
       sum(prompt_tokens + completion_tokens) as tong_token
  from usage_logs
 where created_at > now() - interval '30 days'
 group by 1
 order by 1 desc;
```

---

## 5. Ánh xạ sang code hiện tại

| Trong base hiện tại | Sau khi có DB |
|---|---|
| `frontend/src/utils/storage.ts` | Thay bằng `services/chat/conversationService.ts` gọi backend; store và component không phải sửa |
| `frontend/src/schemas/chatSchema.ts` → `conversationSchema` | Khớp sẵn với bảng `conversations` / `messages` |
| `backend/app/models/` → `Conversation`, `Message` | Thêm lớp ORM tương ứng, giữ nguyên dataclass cho tầng service |
| `backend/app/repositories/` → `InMemory*Repository` | Thêm `Sql*Repository`, đổi 2 dòng khởi tạo trong `main.py` lifespan |
| `backend/app/db/base.py`, `db/session.py` | Điền engine + session theo hướng dẫn sẵn trong file |
| `backend/app/services/chat_service.py` | Nhận thêm repository qua constructor, ghi `messages` + `usage_logs` sau khi stream xong |
| `backend/app/core/security.py` → `get_current_user_id()` | Trả `UUID` từ JWT của Supabase thay vì None |
| `backend/app/core/rate_limit.py` → `_client_key()` | Tự động chuyển sang `user:<id>` ngay khi `get_current_user_id` trả giá trị |

**Thứ tự triển khai đề xuất:** Auth (FR-01/02/10) → conversations/messages (FR-05/06/07)
→ usage_logs + rate limit theo user (FR-09).
