/** Client-side id generation + persisting the JWT session across reloads. */

import { authSessionSchema } from '@/schemas/authSchema';
import { AUTH_STORAGE_KEY } from '@/utils/constants';

import type { AuthSession } from '@/types/auth';

/** Reads the saved session; null (and clears the slot) if missing, malformed, or expired. */
export function loadAuthSession(): AuthSession | null {
  if (typeof localStorage === 'undefined') return null;

  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = authSessionSchema.safeParse(JSON.parse(raw));
    if (!parsed.success) {
      clearAuthSession();
      return null;
    }

    const { expires_at: expiresAt } = parsed.data;
    if (expiresAt != null && expiresAt <= Date.now()) {
      clearAuthSession();
      return null;
    }

    return parsed.data;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function saveAuthSession(session: AuthSession): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function createId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

/** Detects a client-generated id, meaning the conversation is not in the database yet. */
export function isLocalId(id: string): boolean {
  return id.startsWith('local-');
}

/** Id for a memory-only conversation, used by signed-out guests. */
export function createLocalId(): string {
  return `local-${createId()}`;
}
