/** Shared HTTP layer: fetch, Zod validation, ApiError with Vietnamese messages, and SSE decoding. */

import type { ZodType } from 'zod';

import { apiErrorSchema } from '@/schemas/chatSchema';
import { apiUrl } from '@/utils/constants';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

/**
 * Access token của phiên hiện tại.
 *
 * Mô hình phiên: **JWT bearer** (xem docs/API_CONTRACT.md). Backend cấp token khi đăng
 * nhập, frontend gửi lại ở header `Authorization: Bearer <token>`.
 *
 * Giữ ở biến module thay vì đọc localStorage mỗi lần gọi: `services/` không được phụ
 * thuộc store, còn đọc localStorage trong mỗi request thì vừa chậm vừa không chạy được
 * phía server. Store gọi `setAuthToken` mỗi khi phiên đăng nhập đổi.
 */
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

/** Calls the API and returns JSON already checked by Zod. */
export async function request<T>(
  path: string,
  schema: ZodType<T>,
  options: RequestOptions = {},
): Promise<T> {
  const response = await rawRequest(path, options);
  const payload: unknown = await response.json();
  const parsed = schema.safeParse(payload);

  if (!parsed.success) {
    throw new ApiError(
      'Dữ liệu backend trả về không đúng định dạng mong đợi.',
      response.status,
      'schema_mismatch',
    );
  }

  return parsed.data;
}

/** Calls the API and returns the raw Response, for streaming. */
export async function rawRequest(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = 'GET', body, signal, headers = {} } = options;

  const finalHeaders: Record<string, string> = { ...headers };
  if (body !== undefined) finalHeaders['Content-Type'] = 'application/json';
  if (authToken) finalHeaders.Authorization = `Bearer ${authToken}`;

  const response = await fetch(apiUrl(path), {
    method,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (!response.ok) throw await toApiError(response);
  return response;
}

/** Reads an SSE body and yields each `data:` payload, re-joining frames split across network chunks. */
export async function* readSseStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const FRAME_SEPARATOR = /\r?\n\r?\n/;
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      if (signal?.aborted) return;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split(FRAME_SEPARATOR);
      // The tail may be an incomplete frame, so keep it for the next round.
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const payload = extractData(frame);
        if (payload !== null) yield payload;
      }
    }

    // Leftover frame when the stream closes without a trailing blank line.
    const tail = extractData(buffer);
    if (tail !== null) yield tail;
  } finally {
    reader.releaseLock();
  }
}

/** Extracts the `data:` payload of an SSE frame, ignoring comments and `event:`. */
function extractData(frame: string): string | null {
  const DATA_PREFIX = 'data:';
  const parts = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith(DATA_PREFIX))
    .map((line) => line.slice(DATA_PREFIX.length).trimStart());

  return parts.length > 0 ? parts.join('\n') : null;
}

/** Turns an error response into an ApiError with an actionable message. */
async function toApiError(response: Response): Promise<ApiError> {
  let message = `Yêu cầu thất bại (HTTP ${response.status}).`;
  let code: string | undefined;

  try {
    const payload: unknown = await response.json();
    const parsed = apiErrorSchema.safeParse(payload);

    if (parsed.success) {
      message = parsed.data.error.message;
      code = parsed.data.error.code;
    } else if (isValidationErrorPayload(payload)) {
      message = 'Dữ liệu gửi lên không hợp lệ.';
      code = 'validation_error';
    }
  } catch {
    // Body is not JSON, so keep the default message.
  }

  if (response.status === 401) {
    message = 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.';
    code = code ?? 'unauthorized';
  }

  if (response.status === 503) {
    message = `${message} Kiểm tra Ollama đã chạy chưa, hoặc đặt LLM_PROVIDER=mock.`;
  }

  return new ApiError(message, response.status, code);
}

/** Endpoint not implemented yet; callers fall back instead of showing a red error. */
export function isNotImplemented(caught: unknown): boolean {
  return caught instanceof ApiError && (caught.status === 404 || caught.status === 501);
}

/** Session invalid or expired; the store signs the user out. */
export function isUnauthorized(caught: unknown): boolean {
  return caught instanceof ApiError && caught.status === 401;
}

/** FastAPI reports validation errors as `{ detail: [...] }`. */
function isValidationErrorPayload(payload: unknown): boolean {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    'detail' in payload &&
    Array.isArray((payload as { detail: unknown }).detail)
  );
}

/** Turns any thrown value into a message safe to show the user. */
export function toErrorMessage(caught: unknown): string {
  if (caught instanceof ApiError) return caught.message;
  if (caught instanceof TypeError) {
    return 'Không kết nối được backend. Kiểm tra FastAPI đã chạy ở cổng 8000 chưa.';
  }
  if (caught instanceof Error) return caught.message;
  return 'Đã có lỗi không xác định.';
}

/** Detects the user pressing Stop, which is not a real error. */
export function isAbortError(caught: unknown): boolean {
  return caught instanceof DOMException && caught.name === 'AbortError';
}
