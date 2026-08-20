/** Zod schemas for everything crossing the app boundary, i.e. backend responses. */

import { z } from 'zod';

import { CHAT } from '@/utils/constants';

export const roleSchema = z.enum(['system', 'user', 'assistant']);

/** Message sent to the backend; mirrors Pydantic's ChatMessage. */
export const apiMessageSchema = z.object({
  role: roleSchema,
  content: z.string().min(1).max(CHAT.maxMessageLength),
});

/** Body of POST /chat and /chat/stream. */
export const chatRequestSchema = z.object({
  messages: z.array(apiMessageSchema).min(1).max(200),
  model: z.string().nullish(),
  temperature: z.number().min(0).max(2).default(0.7),
  conversation_id: z.string().nullish(),
});

export const chatUsageSchema = z.object({
  prompt_tokens: z.number().int().nullish(),
  completion_tokens: z.number().int().nullish(),
  total_tokens: z.number().int().nullish(),
});

/** Response of POST /chat. */
export const chatResponseSchema = z.object({
  content: z.string(),
  model: z.string(),
  latency_ms: z.number().int(),
  usage: chatUsageSchema.default({}),
});

/** Queue state in front of the model server, included in GET /health. */
export const queueStatusSchema = z.object({
  running: z.number().int(),
  waiting: z.number().int(),
  max_concurrent: z.number().int(),
  max_queue: z.number().int(),
  average_duration_ms: z.number().int().nullish(),
});

/** One SSE event from POST /chat/stream. */
export const streamEventSchema = z.discriminatedUnion('type', [
  // Waiting for a turn on the model; may repeat as the position changes.
  z.object({
    type: z.literal('queued'),
    position: z.number().int(),
    queue_size: z.number().int().nullish(),
    eta_seconds: z.number().int().nullish(),
  }),
  z.object({ type: z.literal('delta'), content: z.string() }),
  z.object({
    type: z.literal('done'),
    model: z.string().optional(),
    latency_ms: z.number().int().optional(),
    usage: chatUsageSchema.optional(),
  }),
  z.object({ type: z.literal('error'), message: z.string() }),
]);

/** Response of GET /health. */
export const healthResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  app_version: z.string(),
  llm_provider: z.string(),
  llm_reachable: z.boolean(),
  model: z.string(),
  // Optional so it still works against a backend without a queue.
  queue: queueStatusSchema.optional(),
});

/** The backend's uniform error shape. */
export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
  }),
});

// --- shapes used inside the app -----------------------------------------
//
// Database conversations pass through conversationSchema.ts first; these are the mapped shapes.

export const chatMessageSchema = z.object({
  id: z.string(),
  role: roleSchema,
  content: z.string(),
  createdAt: z.number(),
  isStreaming: z.boolean().optional(),
  error: z.string().optional(),
});

export const conversationSchema = z.object({
  id: z.string(),
  title: z.string(),
  messages: z.array(chatMessageSchema),
  createdAt: z.number(),
  updatedAt: z.number(),
  isPinned: z.boolean().default(false),
  /** Total messages per the database, known even before the content is fetched. */
  messageCount: z.number().int().nonnegative().default(0),
  /** false = only the list summary is loaded, so `messages` is not the real content yet. */
  isLoaded: z.boolean().default(true),
});

export const conversationListSchema = z.array(conversationSchema);
