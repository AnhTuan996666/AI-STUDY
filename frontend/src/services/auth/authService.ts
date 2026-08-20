/**
 * Auth endpoints.
 *
 * Session model: **JWT bearer** (see docs/API_CONTRACT.md). Login/register return a
 * token; `services/api.ts` attaches it as `Authorization: Bearer <token>` on every
 * request once the store calls `setAuthToken`.
 */

import { authResponseSchema, meResponseSchema } from '@/schemas/authSchema';
import { rawRequest, request } from '@/services/api';
import { API, AUTH } from '@/utils/constants';

import type { AuthResult, User } from '@/types/auth';

/** POST /auth/register — creates the account and returns a token that logs it in. */
export async function register(input: {
  email: string;
  password: string;
  display_name: string;
}): Promise<AuthResult> {
  const payload = await request('/auth/register', authResponseSchema, {
    method: 'POST',
    body: input,
  });
  return toAuthResult(payload);
}

/** POST /auth/login. */
export async function login(input: { email: string; password: string }): Promise<AuthResult> {
  const payload = await request('/auth/login', authResponseSchema, {
    method: 'POST',
    body: input,
  });
  return toAuthResult(payload);
}

/** GET /auth/me — confirms the token is still valid on app start; returns the user. */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<User> {
  return request('/auth/me', meResponseSchema, { signal });
}

/**
 * POST /auth/logout — revokes the token server-side.
 *
 * Errors are swallowed on purpose: the client already cleared its session, so showing a
 * red error here only confuses the user with nothing to act on.
 */
export async function logout(): Promise<void> {
  try {
    await rawRequest('/auth/logout', { method: 'POST' });
  } catch {
    // Nothing to do here; see the note above.
  }
}

/**
 * URL that starts the Google OAuth flow.
 *
 * Navigate the whole page here (not `fetch`): Google blocks loading its consent screen
 * in an iframe/XHR, it must be a top-level navigation. The backend handles the code
 * exchange and redirects back to `redirect_uri` with the token in the query string.
 */
export function googleAuthorizeUrl(): string {
  const redirectUri = `${window.location.origin}${AUTH.callbackPath}`;
  const query = new URLSearchParams({ redirect_uri: redirectUri });

  return `${API.baseUrl}${API.prefix}/auth/google/authorize?${query.toString()}`;
}

/** Đổi response { access_token, expires_in, user } thành phiên client giữ. */
function toAuthResult(payload: {
  access_token: string;
  expires_in?: number | null;
  user: User;
}): AuthResult {
  const expiresAt =
    payload.expires_in != null ? Date.now() + payload.expires_in * 1000 : null;
  return { token: payload.access_token, user: payload.user, expiresAt };
}
