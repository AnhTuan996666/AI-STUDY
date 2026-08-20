/** Reads a client-readable cookie. The auth cookie is httpOnly, so injected script can never see the token. */

export function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;

  const prefix = `${name}=`;

  for (const part of document.cookie.split(';')) {
    const entry = part.trim();
    if (entry.startsWith(prefix)) {
      return decodeURIComponent(entry.slice(prefix.length));
    }
  }

  return null;
}

/** Reads a cookie and parses it as JSON; malformed or non-JSON values return null. */
export function readJsonCookie(name: string): unknown {
  const raw = readCookie(name);
  if (raw === null) return null;

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
