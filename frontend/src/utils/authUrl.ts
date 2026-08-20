/** Builds the Google OAuth entry URL. Lives in utils, not services, because components may import utils only. */

import { API, AUTH } from '@/utils/constants';

/** Navigate the whole page here — Google blocks its consent screen inside an iframe or XHR. */
export function googleAuthorizeUrl(): string {
  const redirectUri = `${window.location.origin}${AUTH.callbackPath}`;
  const query = new URLSearchParams({ redirect_uri: redirectUri });

  return `${API.baseUrl}${API.prefix}/auth/google/authorize?${query.toString()}`;
}
