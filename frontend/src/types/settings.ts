/** Settings and model-list types, inferred from Zod schemas. */

import type { z } from 'zod';

import type { modelListResponseSchema, modelSchema } from '@/schemas/modelSchema';
import type { settingsSchema, themeSchema } from '@/schemas/settingsSchema';

export type Theme = z.infer<typeof themeSchema>;
export type Settings = z.infer<typeof settingsSchema>;
export type ModelInfo = z.infer<typeof modelSchema>;
export type ModelListResponse = z.infer<typeof modelListResponseSchema>;
