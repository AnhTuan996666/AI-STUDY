# AI Chat Web App (MVP)

Web app chat với AI, tự host model mã nguồn mở (Ollama), kiến trúc tách rời 3 layer.

```
┌──────────────────────────┐
│ frontend/  Next.js + TS  │  ← Vercel (free)
└───────────┬──────────────┘
            │ HTTP / SSE
┌───────────▼──────────────┐
│ backend/   FastAPI (Py)  │  ← Render / Railway (free)
└───────────┬──────────────┘
            │ HTTP / NDJSON
┌───────────▼──────────────┐
│ model/     Ollama (Py)   │  ← Local GPU / Cloud GPU
└──────────────────────────┘
```

## 3 folder

| Folder | Ngôn ngữ | Vai trò |
|---|---|---|
| [model/](model/) | Python | Lớp thử nghiệm & client Ollama: test chat terminal, gọi model non-streaming / streaming |
| [backend/](backend/) | Python (FastAPI) | REST + SSE API `/chat`, rate limit, provider abstraction (ollama \| mock) |
| [frontend/](frontend/) | TypeScript (Next.js) | UI chat, render markdown, nhận streaming real-time |

Cả BE và FE tuân theo bộ khung phân tầng cố định:

```
backend/app/     api/ → services/ → repositories/ → db/     (+ models/ schemas/ core/ utils/)
frontend/src/    components/ → hooks/ → store/ → services/  (+ types/ schemas/ utils/ providers/)
```

Chi tiết ràng buộc "tầng nào được import tầng nào": [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md).

## Bắt đầu nhanh

Xem [REMIND.md](REMIND.md) — hướng dẫn cài đặt & chạy từng bước, kèm checklist 7 mốc test.

```powershell
# 1 lệnh setup tất cả
.\scripts\setup.ps1

# chạy backend (terminal 1)
.\scripts\start-backend.ps1

# chạy frontend (terminal 2)
.\scripts\start-frontend.ps1
```

## CI/CD

Mỗi push và pull request đều chạy lint + test cả 3 layer song song; `main` pass xong thì
tự deploy. Cấu hình ở [.github/workflows/](.github/workflows/), hướng dẫn và danh sách
secret cần khai báo ở [docs/CI_CD.md](docs/CI_CD.md).

## Tài liệu

- [docs/BA_PLAN.md](docs/BA_PLAN.md) — Kế hoạch dự án (BA Plan)
- [docs/CI_CD.md](docs/CI_CD.md) — CI/CD, secret, branch protection
- [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) — Chuẩn code BE / FE
- [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) — Thiết kế DB (Supabase/PostgreSQL)
- [docs/TEST_CHECKLIST.md](docs/TEST_CHECKLIST.md) — 7 mốc test của MVP
