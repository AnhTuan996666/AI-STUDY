/** Schema for `GET /models`; without that endpoint the UI falls back to the running model from /health. */

import { z } from 'zod';

export const modelSchema = z.object({
  /** Identifier sent with each chat, e.g. "qwen2.5:7b". */
  id: z.string().min(1),
  /** Display name; falls back to the id. */
  name: z.string().nullish(),
  /** Short description shown under the name in the picker. */
  description: z.string().nullish(),
  size_bytes: z.number().int().nonnegative().nullish(),
  is_default: z.boolean().default(false),
});

export const modelListResponseSchema = z.object({
  models: z.array(modelSchema),
});
