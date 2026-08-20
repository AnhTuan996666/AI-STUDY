'use client';

/** Binds the auth store to the UI so components never touch useSelector/useDispatch. */

import { useCallback } from 'react';

import { useAppDispatch, useAppSelector } from '@/store';
import { adoptToken, errorCleared, signIn, signOut, signUp } from '@/store/auth/authSlice';
import { cleared, loadConversations } from '@/store/chat/chatSlice';
import { pullSettings, settingsReset } from '@/store/settings/settingsSlice';

import type { AuthStatus, User } from '@/types/auth';

interface UseAuthResult {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  isAuthenticated: boolean;
  isBusy: boolean;
  /** The /auth group is missing, so the UI shows a notice rather than a red error. */
  isUnavailable: boolean;
  login: (input: { email: string; password: string }) => Promise<boolean>;
  register: (input: {
    email: string;
    password: string;
    display_name: string;
  }) => Promise<boolean>;
  logout: () => void;
  /** Adopts the token from the Google callback query, then loads the user. */
  adopt: (input: { token: string; expiresAt: number | null }) => Promise<boolean>;
  clearError: () => void;
}

export function useAuth(): UseAuthResult {
  const dispatch = useAppDispatch();

  const user = useAppSelector((state) => state.auth.user);
  const status = useAppSelector((state) => state.auth.status);
  const error = useAppSelector((state) => state.auth.error);
  const isUnavailable = useAppSelector((state) => state.auth.isUnavailable);

  /** Pull the account's data once a session exists; guest state is replaced, never merged. */
  const loadUserData = useCallback(() => {
    void dispatch(loadConversations());
    void dispatch(pullSettings());
  }, [dispatch]);

  const login = useCallback(
    async (input: { email: string; password: string }) => {
      const result = await dispatch(signIn(input));
      const ok = signIn.fulfilled.match(result);
      if (ok) loadUserData();
      return ok;
    },
    [dispatch, loadUserData],
  );

  const register = useCallback(
    async (input: { email: string; password: string; display_name: string }) => {
      const result = await dispatch(signUp(input));
      const ok = signUp.fulfilled.match(result);
      if (ok) loadUserData();
      return ok;
    },
    [dispatch, loadUserData],
  );

  const logout = useCallback(() => {
    void dispatch(signOut()).then(() => {
      // Wipe the previous user's data before anyone else uses this machine.
      dispatch(cleared());
      dispatch(settingsReset());
    });
  }, [dispatch]);

  const adopt = useCallback(
    async (input: { token: string; expiresAt: number | null }) => {
      const result = await dispatch(adoptToken(input));
      const ok = adoptToken.fulfilled.match(result) && result.payload;

      if (ok) loadUserData();
      return ok;
    },
    [dispatch, loadUserData],
  );

  const clearError = useCallback(() => {
    dispatch(errorCleared());
  }, [dispatch]);

  return {
    user,
    status,
    error,
    isAuthenticated: status === 'authenticated',
    isBusy: status === 'authenticating',
    isUnavailable,
    login,
    register,
    logout,
    adopt,
    clearError,
  };
}
