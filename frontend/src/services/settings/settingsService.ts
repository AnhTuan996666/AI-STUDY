/** Settings and model-list endpoints; when they are missing the store falls back instead of erroring. */

import { modelListResponseSchema } from '@/schemas/modelSchema';
import { settingsResponseSchema, settingsSchema } from '@/schemas/settingsSchema';
import { request } from '@/services/api';

import type { ModelInfo, Settings } from '@/types/settings';

/** GET /models — the models the backend currently serves. */
export async function fetchModels(signal?: AbortSignal): Promise<ModelInfo[]> {
  const payload = await request('/models', modelListResponseSchema, { signal });
  return payload.models;
}

/** GET /settings — settings synced to the account. */
export async function fetchSettings(signal?: AbortSignal): Promise<Settings> {
  const payload = await request('/settings', settingsResponseSchema, { signal });
  return payload.settings;
}

/** PUT /settings — saves settings to the server. */
export async function saveSettings(settings: Settings): Promise<Settings> {
  const payload = await request('/settings', settingsResponseSchema, {
    method: 'PUT',
    body: { settings: settingsSchema.parse(settings) },
  });
  return payload.settings;
}
