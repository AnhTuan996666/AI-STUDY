/**
 * Auth slice — JWT bearer session.
 *
 * The token is the credential: it is kept in localStorage (so a reload stays logged in)
 * and pushed into `services/api.ts` via `setAuthToken` so every request carries the
 * `Authorization` header. See docs/API_CONTRACT.md.
 */

import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { isNotImplemented, isUnauthorized, setAuthToken, toErrorMessage } from '@/services/api';
import * as authService from '@/services/auth/authService';
import { clearAuthSession, loadAuthSession, saveAuthSession } from '@/utils/storage';

import type { AuthResult, AuthStatus, User } from '@/types/auth';

export interface AuthState {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  /** The /auth group is missing, so show a notice instead of a red error. */
  isUnavailable: boolean;
}

/** Loads the saved session and primes the API layer so the very first call is authed. */
export function makeInitialAuthState(): AuthState {
  const session = loadAuthSession();
  setAuthToken(session?.token ?? null);

  return {
    user: session?.user ?? null,
    status: session?.user ? 'authenticated' : 'anonymous',
    error: null,
    isUnavailable: false,
  };
}

/** Persist a fresh login everywhere the token needs to live: store, localStorage, API layer. */
function persist(result: AuthResult): void {
  setAuthToken(result.token);
  saveAuthSession({
    token: result.token,
    user: result.user,
    expires_at: result.expiresAt,
  });
}

/** Wipe every trace of the session. */
function forget(): void {
  setAuthToken(null);
  clearAuthSession();
}

const authSlice = createSlice({
  name: 'auth',
  initialState: makeInitialAuthState(),
  reducers: {
    /** Used after `/auth/me` confirms the token — user may have changed, token has not. */
    userRefreshed(state, action: PayloadAction<User>) {
      state.user = action.payload;
      state.status = 'authenticated';
      state.error = null;
    },

    signedOut(state) {
      forget();
      state.user = null;
      state.status = 'anonymous';
      state.error = null;
    },

    errorCleared(state) {
      state.error = null;
    },
  },

  extraReducers(builder) {
    builder
      .addCase(signIn.pending, startAuthenticating)
      .addCase(signUp.pending, startAuthenticating)
      .addCase(signIn.fulfilled, finishAuthenticated)
      .addCase(signUp.fulfilled, finishAuthenticated)
      .addCase(signIn.rejected, failAuthentication)
      .addCase(signUp.rejected, failAuthentication);
  },
});

function startAuthenticating(state: AuthState): void {
  state.status = 'authenticating';
  state.error = null;
  state.isUnavailable = false;
}

function finishAuthenticated(state: AuthState, action: PayloadAction<AuthResult>): void {
  persist(action.payload);
  state.user = action.payload.user;
  state.status = 'authenticated';
  state.error = null;
}

function failAuthentication(
  state: AuthState,
  action: { error: { message?: string }; payload: unknown },
): void {
  const payload = action.payload as AuthFailure | undefined;

  state.status = 'anonymous';
  state.user = null;
  state.isUnavailable = payload?.unavailable ?? false;
  state.error = payload?.message ?? action.error.message ?? 'Đăng nhập thất bại.';
}

export const { userRefreshed, signedOut, errorCleared } = authSlice.actions;
export const authReducer = authSlice.reducer;

// --- thunk ---------------------------------------------------------------

interface AuthFailure {
  message: string;
  /** Endpoint not implemented, which is a different case from a wrong password. */
  unavailable: boolean;
}

function toFailure(caught: unknown): AuthFailure {
  if (isNotImplemented(caught)) {
    return {
      message: 'Backend chưa có API đăng nhập. Xem docs/API_CONTRACT.md để cài đặt nhóm /auth.',
      unavailable: true,
    };
  }
  return { message: toErrorMessage(caught), unavailable: false };
}

export const signIn = createAsyncThunk<
  AuthResult,
  { email: string; password: string },
  { rejectValue: AuthFailure }
>('auth/signIn', async (input, { rejectWithValue }) => {
  try {
    return await authService.login(input);
  } catch (caught) {
    return rejectWithValue(toFailure(caught));
  }
});

export const signUp = createAsyncThunk<
  AuthResult,
  { email: string; password: string; display_name: string },
  { rejectValue: AuthFailure }
>('auth/signUp', async (input, { rejectWithValue }) => {
  try {
    return await authService.register(input);
  } catch (caught) {
    return rejectWithValue(toFailure(caught));
  }
});

export const signOut = createAsyncThunk<void, void>('auth/signOut', async (_, { dispatch }) => {
  await authService.logout();
  dispatch(signedOut());
});

/**
 * Adopts a token that arrived via the Google callback query string, then loads the user.
 *
 * The callback page hands us the raw token; we store it and hit `/auth/me` to fill in
 * who it belongs to.
 */
export const adoptToken = createAsyncThunk<boolean, { token: string; expiresAt: number | null }>(
  'auth/adoptToken',
  async ({ token, expiresAt }, { dispatch }) => {
    setAuthToken(token);
    try {
      const user = await authService.fetchCurrentUser();
      saveAuthSession({ token, user, expires_at: expiresAt });
      dispatch(userRefreshed(user));
      return true;
    } catch (caught) {
      forget();
      if (isUnauthorized(caught)) dispatch(signedOut());
      return false;
    }
  },
);

/** Confirms the token on startup; a missing `/auth/me` leaves the state alone rather than signing out. */
export const restoreSession = createAsyncThunk<void, void>(
  'auth/restoreSession',
  async (_, { dispatch, getState }) => {
    const state = getState() as { auth: AuthState };

    // No stored token, so skip the network call.
    if (!state.auth.user) return;

    try {
      dispatch(userRefreshed(await authService.fetchCurrentUser()));
    } catch (caught) {
      if (isUnauthorized(caught)) {
        dispatch(signedOut());
        return;
      }
      // Without /auth/me nothing can be concluded, so leave the current state alone.
    }
  },
);
