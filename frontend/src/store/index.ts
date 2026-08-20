/** Redux store setup and typed hooks. */

import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector, useStore } from 'react-redux';

import { authReducer, makeInitialAuthState, restoreSession } from '@/store/auth/authSlice';
import { chatReducer, loadConversations } from '@/store/chat/chatSlice';
import {
  loadModels,
  makeInitialSettingsState,
  pullSettings,
  settingsReducer,
} from '@/store/settings/settingsSlice';

/** Builds the store and kicks off data loading; nothing is read from or written to localStorage any more. */
export function makeStore() {
  const store = configureStore({
    reducer: {
      chat: chatReducer,
      auth: authReducer,
      settings: settingsReducer,
    },
    preloadedState: {
      auth: makeInitialAuthState(),
      settings: makeInitialSettingsState(),
    },
  });

  // The model list needs no session, so it can be fetched right away.
  void store.dispatch(loadModels());

  // The rest bail out early when signed out, and each handles its own errors.
  void store.dispatch(restoreSession()).then(() => {
    void store.dispatch(loadConversations());
    void store.dispatch(pullSettings());
  });

  return store;
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];

// Use these typed hooks instead of the raw useDispatch/useSelector.
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
export const useAppStore = useStore.withTypes<AppStore>();
