# CI/CD

Repo: <https://github.com/AnhTuan996666/AI-STUDY>

Hai workflow trong [`.github/workflows/`](../.github/workflows/):

| File | Chạy khi nào | Làm gì |
|---|---|---|
| `ci.yml` | push lên `main`, mọi pull request, hoặc bấm tay | Lint + test cả 3 layer, song song |
| `deploy.yml` | CI trên `main` **pass xong**, hoặc bấm tay | Deploy frontend lên Vercel, backend lên Render |

---

## CI

Ba job chạy **song song**, không phụ thuộc nhau:

| Job | Lệnh | Cần dịch vụ ngoài? |
|---|---|---|
| `model` | `ruff check .` → `pytest -q` | Không — test dùng `httpx.MockTransport` |
| `backend` | `ruff check .` → `pytest -q` | Không — chạy với `LLM_PROVIDER=mock` |
| `frontend` | `npm run typecheck` → `lint` → `build` | Không |

Job thứ tư tên `ci` gom kết quả của cả ba. Khi đặt branch protection, **chỉ cần chọn
một check duy nhất là `ci`** thay vì liệt kê từng job — thêm bớt job sau này không phải
vào sửa lại cấu hình bảo vệ nhánh.

### Phiên bản

```yaml
PYTHON_VERSION: '3.12'
NODE_VERSION: '22'
```

Máy dev đang dùng **Python 3.14**. CI cố tình chạy 3.12 cho ổn định wheel; nếu bạn muốn
CI khớp hệt máy dev thì sửa `PYTHON_VERSION` trong `ci.yml`.

### Tăng tốc

- `cache: pip` và `cache: npm` theo file khoá của từng thư mục.
- `concurrency` huỷ run cũ khi đẩy commit mới lên cùng nhánh.

---

## CD

`deploy.yml` chỉ chạy sau khi CI **pass trên `main`**. Chưa cấu hình secret thì nó
**không đỏ** — chỉ ghi một `notice` rồi bỏ qua, để bạn dùng CI trước, deploy sau.

### Secrets cần khai báo

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`.

| Secret | Lấy ở đâu | Thiếu thì sao |
|---|---|---|
| `VERCEL_TOKEN` | vercel.com → Account Settings → Tokens | Bỏ qua deploy frontend |
| `VERCEL_ORG_ID` | `frontend/.vercel/project.json` sau khi chạy `npx vercel link` | Bỏ qua deploy frontend |
| `VERCEL_PROJECT_ID` | cùng file trên | Bỏ qua deploy frontend |
| `RENDER_DEPLOY_HOOK_URL` | Render → service → Settings → Deploy Hook | Bỏ qua deploy backend |

Cả 3 secret của Vercel phải có **đủ** thì bước frontend mới chạy.

> Secret không đọc được trong `if` ở cấp job của GitHub Actions, nên phần kiểm tra nằm ở
> một step riêng tên `Check secrets` rồi các step sau xem output của nó.

### Biến môi trường phía Vercel

Workflow **không** truyền biến môi trường sang Vercel. Khai báo trực tiếp trong dashboard
Vercel (`Settings` → `Environment Variables`):

| Biến | Giá trị |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | URL backend trên Render, vd `https://ai-study-api.onrender.com` |

### Biến môi trường phía Render

Khai báo trong dashboard Render. Tối thiểu:

| Biến | Ghi chú |
|---|---|
| `LLM_PROVIDER` | `ollama` hoặc `mock` |
| `OLLAMA_BASE_URL` | URL máy chạy Ollama |
| `CORS_ORIGINS` | **Bắt buộc là domain cụ thể**, ngăn cách dấu phẩy. Không dùng `*` |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Cho luồng đăng nhập Google |

> `CORS_ORIGINS` không được để `*`: frontend gửi cookie phiên (`credentials: 'include'`),
> mà trình duyệt chặn cookie với origin `*`. Chi tiết: [API_CONTRACT.md](API_CONTRACT.md).

---

## Chạy lại đúng những gì CI chạy, ở máy

```powershell
cd model    ; .\.venv\Scripts\Activate.ps1 ; task check
cd ..\backend ; .\.venv\Scripts\Activate.ps1 ; task check
cd ..\frontend ; npm run typecheck ; npm run lint ; npm run build
```

Hoặc một lệnh cho cả ba: `.\scripts\run-tests.ps1`.

---

## Gợi ý branch protection

`Settings` → `Branches` → `Add rule` cho `main`:

- ☑ Require a pull request before merging
- ☑ Require status checks to pass → chọn **`ci`**
- ☑ Require branches to be up to date before merging
