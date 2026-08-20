/** Chat endpoints; the HTTP work itself lives in services/api.ts. */

import { ApiError, rawRequest, readSseStream, request } from '@/services/api';
import {
  chatResponseSchema,
  healthResponseSchema,
  streamEventSchema,
} from '@/schemas/chatSchema';
import type { ChatResponse, HealthResponse, SendChatParams, StreamEvent } from '@/types/chat';

/** GET /health — feeds the system status indicator. */
export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request('/health', healthResponseSchema, { signal });
}

/** POST /chat — waits for the complete reply (FR-03). */
export function sendChat({
  messages,
  temperature = 0.7,
  model,
  conversationId,
  signal,
}: SendChatParams): Promise<ChatResponse> {
  return request('/chat', chatResponseSchema, {
    method: 'POST',
    body: { messages, temperature, model, conversation_id: conversationId },
    signal,
  });
}

/** POST /chat/stream — yields Zod-checked StreamEvents (FR-04); malformed frames are skipped. */
export async function* streamChat({
  messages,
  temperature = 0.7,
  model,
  conversationId,
  signal,
}: SendChatParams): AsyncGenerator<StreamEvent> {
  const response = await rawRequest('/chat/stream', {
    method: 'POST',
    // When `conversation_id` is present the backend also stores the messages.
    body: { messages, temperature, model, conversation_id: conversationId },
    headers: { Accept: 'text/event-stream' },
    signal,
  });

  if (!response.body) throw new ApiError('Backend không trả về luồng dữ liệu.');

  for await (const payload of readSseStream(response.body, signal)) {
    const event = parseEvent(payload);
    if (event) yield event;
  }
}

function parseEvent(payload: string): StreamEvent | null {
  try {
    const parsed = streamEventSchema.safeParse(JSON.parse(payload));
    return parsed.success ? parsed.data : null;
  } catch {
    // Skip malformed frames rather than killing the whole stream.
    return null;
  }
}
