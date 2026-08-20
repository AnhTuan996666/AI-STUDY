# frontend/ — Next.js 16 + TypeScript

Giao diện chat. Nhận streaming từ backend qua SSE và hiển thị dần từng token.

## Cấu trúc

```
frontend/
├── src/
│   ├── app/                        # App Router
│   │   ├── layout.tsx              # bọc StoreProvider
│   │   ├── page.tsx
│   │   └── globals.css             # Tailwind v4 + token màu + style markdown
│   │
│   ├── components/
│   │   ├── common/                 # dùng lại được, không biết gì về nghiệp vụ
│   │   │   ├── Button/
│   │   │   ├── IconButton/
│   │   │   ├── Spinner/
│   │   │   └── StatusBadge/
│   │   │
│   │   ├── layout/
│   │   │   ├── Header/             # tiêu đề + badge trạng thái backend
│   │   │   └── Sidebar/            # danh sách hội thoại (FR-06, FR-07)
│   │   │
│   │   └── chat/
│   │       ├── ChatContainer/      # index.tsx = loader client-only; ChatContainer.tsx = UI
│   │       ├── MessageList/
│   │       ├── MessageBubble/      # render markdown (FR-08)
│   │       └── ChatInput/
│   │
│   ├── services/                   # gọi API
│   │   ├── api.ts                  # fetch + ApiError + Zod + giải mã SSE
│   │   └── chat/chatService.ts     # /chat, /chat/stream, /health
│   │
│   ├── store/                      # Redux Toolkit
│   │   ├── index.ts                # configureStore + typed hooks + ghi localStorage
│   │   └── chat/chatSlice.ts       # state + reducer + thunk sendMessage
│   │
│   ├── hooks/
│   │   └── chat/
│   │       ├── useChat.ts          # nối store với UI
│   │       └── useHealth.ts
│   │
│   ├── types/chat.ts               # kiểu, suy ra từ Zod schema
│   ├── schemas/chatSchema.ts       # validate mọi dữ liệu qua biên (API + localStorage)
│   ├── utils/                      # constants, format, validation, storage
│   └── providers/StoreProvider.tsx
│
├── public/
├── package.json / tsconfig.json / next.config.ts
└── .env.local
```

Alias `@/*` trỏ tới `./src/*` — luôn import bằng `@/components/...`, không dùng `../../..`.

## Quy tắc phân tầng

```
components/  →  hooks/  →  store/  →  services/
  hiển thị      binding    state      HTTP
```

- Component **không gọi `fetch`** và **không `useSelector`/`useDispatch` trực tiếp** —
  chỉ dùng hook. Đổi cấu trúc store về sau không phải sửa component.
- `services/` không biết gì về Redux; `store/` không biết gì về React.
- `components/common/` không được import từ `store/` hay `services/`.

## Vì sao không dùng `EventSource`

`EventSource` của trình duyệt chỉ hỗ trợ **GET** và không gửi được body. API của ta là
`POST /chat/stream` kèm JSON, nên phải tự đọc `response.body` (ReadableStream) và tách
frame SSE trong [src/services/api.ts](src/services/api.ts). Bộ giải mã xử lý cả trường hợp
một frame bị cắt làm đôi giữa hai chunk mạng.

## Vì sao `ChatContainer` là client-only

Store khởi tạo từ `localStorage`. Nếu vẫn render phía server, HTML server (rỗng) sẽ khác
HTML client (có lịch sử) và gây lỗi hydration. Dùng `next/dynamic` với `ssr: false` trong
[src/components/chat/ChatContainer/index.tsx](src/components/chat/ChatContainer/index.tsx).

## Vì sao có cả `types/` và `schemas/`

TypeScript chỉ kiểm tra lúc biên dịch. Dữ liệu **đi qua biên** (response backend, state cũ
trong localStorage) có thể lệch hợp đồng lúc chạy, nên được Zod validate ở `schemas/`.
`types/chat.ts` suy ra kiểu từ chính schema đó (`z.infer`) để hai bên không bao giờ lệch nhau.

## Chạy

```powershell
npm run dev        # http://localhost:3000
npm run typecheck
npm run lint
npm run build
```

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | URL backend FastAPI |

## Thêm một miền mới (ví dụ `orders`)

1. `src/schemas/orderSchema.ts` → `src/types/order.ts` (suy ra bằng `z.infer`)
2. `src/services/order/orderService.ts`
3. `src/store/order/orderSlice.ts` → đăng ký reducer trong `src/store/index.ts`
4. `src/hooks/order/useOrderList.ts`
5. `src/components/orders/...` và route `src/app/orders/page.tsx`
