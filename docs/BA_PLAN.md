# TÀI LIỆU KẾ HOẠCH DỰ ÁN (BA PLAN)

**Xây dựng Web App Chatbot AI (Tự host mô hình mã nguồn mở)**

| | |
|---|---|
| Phiên bản | 1.0 |
| Ngày | 2026-08-20 |
| Trạng thái | Đang triển khai — Giai đoạn 1 (MVP Free) |

---

## 1. TỔNG QUAN DỰ ÁN

**Tên dự án:** AI Chat Web App (MVP)

**Mục tiêu kinh doanh:** Xây dựng một ứng dụng web chat với AI, tự host model mã nguồn mở,
triển khai theo mô hình chi phí thấp/miễn phí ở giai đoạn đầu, có khả năng mở rộng dần khi
có traffic và ngân sách.

**Đối tượng người dùng:**

- Giai đoạn 1: Bản thân/nhóm nhỏ dùng thử, bạn bè, early adopter
- Giai đoạn 2+: Người dùng công khai (nếu mở rộng)

**Ràng buộc chính:**

- Ngân sách ban đầu = 0 hoặc gần 0 (free tier)
- Hạ tầng GPU giới hạn (máy cá nhân hoặc free cloud)
- Đội ngũ: solo hoặc nhóm nhỏ

---

## 2. PHẠM VI DỰ ÁN (SCOPE)

### 2.1. Trong phạm vi (In-scope) — MVP

| Hạng mục | Mô tả | Trạng thái base hiện tại |
|---|---|---|
| Đăng ký/Đăng nhập | Email/password hoặc OAuth (Google) | ☐ Chưa làm |
| Chat 1-1 với AI | Gửi tin nhắn, nhận phản hồi dạng streaming | ☑ Xong |
| Lưu lịch sử hội thoại | Xem lại, tiếp tục hội thoại cũ | ◐ localStorage (chưa có DB) |
| Quản lý nhiều cuộc trò chuyện | Tạo mới, đổi tên, xóa conversation | ◐ localStorage |
| Model server tự host | Chạy model mã nguồn mở qua Ollama | ☑ Xong |
| Giới hạn sử dụng cơ bản | Rate limit đơn giản theo user (chống spam) | ◐ Theo IP, in-memory |

### 2.2. Ngoài phạm vi (Out-of-scope) — để giai đoạn sau

- Upload file/hình ảnh, phân tích tài liệu
- Tạo artifact (code preview, canvas...)
- Tìm kiếm web real-time
- Multi-model (chọn model khác nhau)
- Thanh toán/gói trả phí
- Ứng dụng mobile riêng
- Fine-tune model theo dữ liệu riêng

---

## 3. STAKEHOLDERS & VAI TRÒ

| Vai trò | Trách nhiệm |
|---|---|
| Product Owner | Quyết định tính năng, ưu tiên |
| Developer (FE/BE) | Bạn hoặc thành viên nhóm |
| AI/Infra | Setup & vận hành model server |
| QA | Test thủ công trước mỗi lần release |

---

## 4. YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS)

| ID | Yêu cầu | Mô tả chi tiết | Ưu tiên | Hiện trạng |
|---|---|---|---|---|
| FR-01 | Đăng ký tài khoản | User tạo tài khoản bằng email hoặc Google | Cao | ☐ |
| FR-02 | Đăng nhập | User đăng nhập, giữ session | Cao | ☐ |
| FR-03 | Gửi tin nhắn chat | User nhập text, gửi tới AI, nhận phản hồi | Cao | ☑ `POST /api/v1/chat` |
| FR-04 | Streaming phản hồi | Phản hồi AI hiển thị dần theo thời gian thực | Cao | ☑ `POST /api/v1/chat/stream` (SSE) |
| FR-05 | Lưu lịch sử hội thoại | Mỗi tin nhắn được lưu vào DB, gắn với user + conversation | Cao | ◐ localStorage |
| FR-06 | Danh sách hội thoại | Sidebar hiển thị các cuộc chat trước đó | Trung bình | ◐ localStorage |
| FR-07 | Tạo/xóa/đổi tên hội thoại | CRUD cơ bản cho conversation | Trung bình | ◐ localStorage |
| FR-08 | Markdown/code rendering | Hiển thị code block, bảng, danh sách đúng định dạng | Trung bình | ☑ react-markdown + remark-gfm |
| FR-09 | Rate limiting | Giới hạn số tin nhắn/phút mỗi user | Trung bình | ◐ Theo IP |
| FR-10 | Đăng xuất | Kết thúc session | Cao | ☐ |

**Chú thích:** ☑ xong · ◐ xong một phần · ☐ chưa làm

---

## 5. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL REQUIREMENTS)

| ID | Yêu cầu | Mô tả | Cách đáp ứng trong base |
|---|---|---|---|
| NFR-01 | Chi phí | Giai đoạn 1: $0, dùng free tier toàn bộ | Ollama local + Vercel/Render free |
| NFR-02 | Hiệu năng | First token < 5s trên free infra | SSE, header `X-Accel-Buffering: no`; đo TTFT trong log & smoke test |
| NFR-03 | Bảo mật | API key/model server không lộ ra frontend; mật khẩu hash | FE chỉ biết URL backend; Ollama không expose ra internet; Supabase Auth sẽ lo hashing |
| NFR-04 | Khả năng mở rộng | Kiến trúc tách rời để dễ nâng cấp từng phần | 3 folder độc lập + interface `LLMProvider` |
| NFR-05 | Uptime | Chấp nhận downtime ở giai đoạn free | Health badge trên UI, thông báo lỗi rõ ràng |
| NFR-06 | Khả năng bảo trì | Code có cấu trúc rõ ràng, dễ thay model/API | Chuẩn code thống nhất (xem CODING_STANDARDS.md), 39 test tự động |

---

## 6. KIẾN TRÚC GIẢI PHÁP (SOLUTION ARCHITECTURE)

```
┌─────────────────┐
│  Next.js (FE)   │  ← Vercel (Free)
└────────┬────────┘
         │ HTTPS + SSE
┌────────▼────────┐
│ FastAPI (BE)    │  ← Render/Railway (Free)
└───┬─────────┬───┘
    │         │
┌───▼────┐ ┌──▼──────────────┐
│Supabase│ │ Ollama (Model)  │ ← Local máy/Cloud GPU free
│DB+Auth │ │ qua tunnel      │
└────────┘ └─────────────────┘
```

### Công nghệ

| Layer | Ngôn ngữ | Công nghệ | Lý do chọn |
|---|---|---|---|
| Model serving | Python | Ollama + httpx | Chuẩn ngành, ecosystem AI |
| Backend API | Python | FastAPI | Đồng bộ với model layer, async tốt cho streaming |
| Frontend | TypeScript | Next.js 16 + Tailwind 4 | Chuẩn cho web hiện đại |
| Database | — | Supabase (PostgreSQL) | Free tier ~500MB |
| Auth | — | Supabase Auth | Free, hỗ trợ Google OAuth |
| Streaming | — | Server-Sent Events (SSE) | Đơn giản hơn WebSocket, hợp mô hình 1 chiều |

### Vì sao tách `LLMProvider` thành interface

Đổi model server (Ollama → vLLM → API bên thứ 3) chỉ cần viết thêm một lớp con trong
`backend/app/services/llm/`, không đụng tới tầng API hay frontend. Đáp ứng NFR-04, NFR-06
và giảm rủi ro "chất lượng model open-source thấp hơn kỳ vọng" trong mục 9.

---

## 7. USER STORIES (MVP)

1. Là **người dùng mới**, tôi muốn đăng ký tài khoản để bắt đầu sử dụng app. *(FR-01)*
2. Là **người dùng đã đăng nhập**, tôi muốn gửi tin nhắn và thấy AI trả lời theo thời gian
   thực để trải nghiệm mượt mà. *(FR-03, FR-04)*
3. Là **người dùng**, tôi muốn xem lại các cuộc hội thoại cũ để tiếp tục ngữ cảnh đã trao đổi. *(FR-05, FR-06)*
4. Là **người dùng**, tôi muốn tạo cuộc hội thoại mới để tách biệt các chủ đề khác nhau. *(FR-07)*
5. Là **quản trị viên**, tôi muốn giới hạn số request mỗi user để tránh chi phí/tải phát sinh
   ngoài kiểm soát. *(FR-09)*

---

## 8. LỘ TRÌNH TRIỂN KHAI (ROADMAP)

### Giai đoạn 0 — Chuẩn bị (1 tuần)

- [x] Setup repo, chọn stack
- [ ] Tạo tài khoản Vercel/Render/Supabase
- [ ] Cài Ollama, tải thử model, test chất lượng phản hồi

### Giai đoạn 1 — MVP Free (2-4 tuần)

- [x] Dựng khung project (scaffold) cho 3 layer
- [x] Xây API chat cơ bản (không streaming)
- [x] Thêm streaming (SSE)
- [x] Xây UI chat tối giản
- [ ] Xây database schema (users, conversations, messages) — thiết kế xong, chưa triển khai
- [ ] Tích hợp Auth (Supabase)
- [ ] Deploy free tier toàn bộ, test nội bộ

### Giai đoạn 2 — Ổn định & mở rộng nhẹ

- [ ] Chuyển model server từ local → GPU cloud thuê theo giờ (RunPod/Vast.ai)
- [ ] Rate limiting theo user (Redis) thay vì in-memory theo IP
- [ ] Theo dõi lỗi (Sentry) & log usage

### Giai đoạn 3 — Production

- [ ] Nâng cấp backend/DB lên gói trả phí
- [ ] Chuyển sang vLLM để tăng throughput
- [ ] Thêm tính năng: upload file, multi-model, gói trả phí

---

## 9. RỦI RO & GIẢI PHÁP (RISK LOG)

| Rủi ro | Mức độ | Giải pháp giảm thiểu | Đã xử lý trong base? |
|---|---|---|---|
| Free GPU/backend không ổn định | Cao | Thông báo rõ cho user giai đoạn beta; có cơ chế retry | ☑ Health badge + thông điệp lỗi tiếng Việt + nút Dừng |
| Chi phí GPU tăng đột ngột khi scale | Trung bình | Rate limit chặt, theo dõi usage sát sao | ☑ Rate limit + log token mỗi lượt |
| Chất lượng model open-source thấp hơn kỳ vọng | Trung bình | Test kỹ nhiều model trước khi chọn, có thể đổi model sau | ☑ Đổi model bằng 1 biến `.env`; `step0_check.py` liệt kê model |
| Bảo mật dữ liệu người dùng | Cao | Hash mật khẩu, dùng HTTPS, không log nội dung chat nhạy cảm | ☑ Log chỉ ghi độ dài/token, không ghi nội dung |
| ngrok tunnel không ổn định (dev) | Trung bình | Cân nhắc Cloudflare Tunnel khi lên giai đoạn 2 | ☐ Giai đoạn 2 |
| Không có GPU khi phát triển frontend | Trung bình | Provider `mock` để dev/test không cần model thật | ☑ `LLM_PROVIDER=mock` |

---

## 10. TIÊU CHÍ THÀNH CÔNG (SUCCESS METRICS) — MVP

| Tiêu chí | Cách đo | Trạng thái |
|---|---|---|
| App chạy end-to-end: đăng ký → chat → lưu lịch sử → đăng xuất | Test thủ công | ◐ Chat + lịch sử xong; auth chưa |
| First token < 5-8s trên free infra | `scripts/smoke_test.py` in ra TTFT | ☑ Đo được tự động |
| Không phát sinh chi phí giai đoạn 1 | Kiểm tra dashboard các dịch vụ | ☐ Chưa deploy |
| Có 5-10 người dùng thử nghiệm và thu thập phản hồi | Khảo sát | ☐ Chưa mở |

---

## 11. BƯỚC TIẾP THEO ĐỀ XUẤT

1. ~~Chốt stack cụ thể~~ ☑ Next.js + FastAPI + Supabase + Ollama
2. ~~Thiết kế chi tiết database schema~~ ☑ Xem [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
3. ~~Dựng khung project (scaffold) cho FE và BE~~ ☑ Xong, kèm test tự động
4. **Cài Ollama, chạy thử model đầu tiên** ← đang ở bước này, xem [REMIND.md](../REMIND.md) mục 0
5. Tích hợp Supabase Auth (FR-01, FR-02, FR-10)
6. Chuyển lưu trữ hội thoại từ localStorage sang PostgreSQL (FR-05)
