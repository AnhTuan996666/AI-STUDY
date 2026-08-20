/** Conversation schemas from the database; the mappers below are the only place snake_case becomes camelCase. */

import { z } from 'zod';

import { roleSchema } from '@/schemas/chatSchema';

import type { ChatMessage, Conversation } from '@/types/chat';

export const messageDtoSchema = z.object({
  id: z.string(),
  role: roleSchema,
  content: z.string(),
  /** ISO 8601. */
  created_at: z.string(),
});

/** Summary for the sidebar list; messages are omitted to keep it light. */
export const conversationSummaryDtoSchema = z.object({
  id: z.string(),
  title: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  is_pinned: z.boolean().default(false),
  message_count: z.number().int().nonnegative().default(0),
});

/** Full form, used when opening a conversation. */
export const conversationDtoSchema = conversationSummaryDtoSchema.extend({
  messages: z.array(messageDtoSchema).default([]),
});

export const conversationListResponseSchema = z.object({
  conversations: z.array(conversationSummaryDtoSchema),
});

export const conversationResponseSchema = z.object({
  conversation: conversationDtoSchema,
});

// --- mapper --------------------------------------------------------------

type ConversationSummaryDto = z.infer<typeof conversationSummaryDtoSchema>;
type ConversationDto = z.infer<typeof conversationDtoSchema>;
type MessageDto = z.infer<typeof messageDtoSchema>;

/** A broken ISO string falls back to now, so NaN never reaches the state. */
function toTimestamp(iso: string): number {
  const value = Date.parse(iso);
  return Number.isNaN(value) ? Date.now() : value;
}

export function toChatMessage(dto: MessageDto): ChatMessage {
  return {
    id: dto.id,
    role: dto.role,
    content: dto.content,
    createdAt: toTimestamp(dto.created_at),
  };
}

/** Summary form: `messages: []` means "not loaded yet", not "empty" — `messageCount` says what really exists. */
export function toConversationSummary(dto: ConversationSummaryDto): Conversation {
  return {
    id: dto.id,
    title: dto.title,
    messages: [],
    createdAt: toTimestamp(dto.created_at),
    updatedAt: toTimestamp(dto.updated_at),
    isPinned: dto.is_pinned,
    messageCount: dto.message_count,
    isLoaded: false,
  };
}

export function toConversation(dto: ConversationDto): Conversation {
  return {
    ...toConversationSummary(dto),
    messages: dto.messages.map(toChatMessage),
    isLoaded: true,
  };
}
