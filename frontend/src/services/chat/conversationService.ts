/** Reads and writes conversations in the database; replaces the old localStorage storage entirely. */

import { request, rawRequest } from '@/services/api';
import {
  conversationListResponseSchema,
  conversationResponseSchema,
  toConversation,
  toConversationSummary,
} from '@/schemas/conversationSchema';

import type { Conversation } from '@/types/chat';

/** GET /conversations — summaries for the sidebar, without messages. */
export async function listConversations(signal?: AbortSignal): Promise<Conversation[]> {
  const payload = await request('/conversations', conversationListResponseSchema, { signal });
  return payload.conversations.map(toConversationSummary);
}

/** GET /conversations/{id} — the full conversation with all messages. */
export async function fetchConversation(
  id: string,
  signal?: AbortSignal,
): Promise<Conversation> {
  const payload = await request(
    `/conversations/${encodeURIComponent(id)}`,
    conversationResponseSchema,
    { signal },
  );
  return toConversation(payload.conversation);
}

/** POST /conversations — creates an empty conversation before the first message. */
export async function createConversation(title: string): Promise<Conversation> {
  const payload = await request('/conversations', conversationResponseSchema, {
    method: 'POST',
    body: { title },
  });
  return toConversation(payload.conversation);
}

/** PATCH /conversations/{id} — rename, or pin and unpin. */
export async function updateConversation(
  id: string,
  patch: { title?: string; is_pinned?: boolean },
): Promise<Conversation> {
  const payload = await request(
    `/conversations/${encodeURIComponent(id)}`,
    conversationResponseSchema,
    { method: 'PATCH', body: patch },
  );
  return toConversation(payload.conversation);
}

/** DELETE /conversations/{id}. */
export async function deleteConversation(id: string): Promise<void> {
  await rawRequest(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
