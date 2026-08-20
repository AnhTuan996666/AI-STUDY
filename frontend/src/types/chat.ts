/** Chat domain types; anything crossing the network is inferred from Zod so the two can never drift apart. */

import type { z } from 'zod';

import type {
  apiMessageSchema,
  chatMessageSchema,
  chatResponseSchema,
  chatUsageSchema,
  conversationSchema,
  healthResponseSchema,
  queueStatusSchema,
  roleSchema,
  streamEventSchema,
} from '@/schemas/chatSchema';

// --- inferred from schemas -----------------------------------------------

export type Role = z.infer<typeof roleSchema>;
export type ApiMessage = z.infer<typeof apiMessageSchema>;
export type ChatUsage = z.infer<typeof chatUsageSchema>;
export type ChatResponse = z.infer<typeof chatResponseSchema>;
export type StreamEvent = z.infer<typeof streamEventSchema>;
export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type QueueStatus = z.infer<typeof queueStatusSchema>;
export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type Conversation = z.infer<typeof conversationSchema>;

// --- UI-only types -------------------------------------------------------

/** `queued` = sent, but waiting in line for the model. */
export type ChatStatus = 'idle' | 'queued' | 'streaming' | 'error';

/** Sync state of the conversation list against the database. */
export type SyncStatus = 'idle' | 'loading' | 'ready' | 'error';

/** Position in the queue for the pending turn. */
export interface QueuePlace {
  position: number;
  queueSize: number | null;
  etaSeconds: number | null;
}

/** Backend probe result, used by the status indicators in the header and sidebar. */
export type HealthState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: HealthResponse }
  | { kind: 'down' };

/** Parameters for one chat turn. */
export interface SendChatParams {
  messages: ApiMessage[];
  temperature?: number;
  model?: string;
  /** With an id the backend stores the messages; without one the turn is not saved. */
  conversationId?: string;
  signal?: AbortSignal;
}
