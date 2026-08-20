/** Shared constants; business values never get scattered across components. */

export const API = {
  /** URL backend FastAPI. */
  baseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, ''),
  prefix: '/api/v1',
} as const;

export const CHAT = {
  /** Recent messages sent as context; the backend trims again on its side. */
  maxContextMessages: 20,
  /** Max message length, matching the backend schema's limit. */
  maxMessageLength: 32_000,
  /** Max length of an auto-generated conversation title. */
  maxTitleLength: 40,
  defaultTitle: 'Hội thoại mới',
} as const;

/** localStorage key for the persisted JWT session (token + user). */
export const AUTH_STORAGE_KEY = 'ai-chat:auth';

/** localStorage key caching the theme, so the first paint matches before the store loads. */
export const THEME_STORAGE_KEY = 'ai-chat:theme';

export const SETTINGS = {
  /** Default temperature before the user changes it. */
  defaultTemperature: 0.7,
  minTemperature: 0,
  maxTemperature: 2,
  temperatureStep: 0.1,
} as const;

export const AUTH = {
  minPasswordLength: 8,
  maxPasswordLength: 128,
  maxDisplayNameLength: 60,
  /** Frontend path the backend returns the user to after Google authenticates. */
  callbackPath: '/auth/callback',
} as const;

/** How often to re-check backend health, in milliseconds. */
export const HEALTH_POLL_INTERVAL_MS = 30_000;

export function apiUrl(path: string): string {
  return `${API.baseUrl}${API.prefix}${path}`;
}
