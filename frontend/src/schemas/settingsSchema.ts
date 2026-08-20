/** Settings schemas; settings live in the database, via GET/PUT /settings. */

import { z } from 'zod';

import { SETTINGS } from '@/utils/constants';

export const themeSchema = z.enum(['system', 'light', 'dark']);

export const settingsSchema = z.object({
  theme: themeSchema.default('system'),
  /** null = use the backend's default model. */
  model: z.string().nullable().default(null),
  temperature: z
    .number()
    .min(SETTINGS.minTemperature)
    .max(SETTINGS.maxTemperature)
    .default(SETTINGS.defaultTemperature),
  /** true: Enter sends, Shift+Enter breaks. false is the reverse. */
  send_on_enter: z.boolean().default(true),
  /** Show prompt suggestions on the welcome screen. */
  show_suggestions: z.boolean().default(true),
});

/** Response of GET /settings, wrapped one level to match the backend's shape. */
export const settingsResponseSchema = z.object({
  settings: settingsSchema,
});
