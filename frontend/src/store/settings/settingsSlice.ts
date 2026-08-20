/** Settings slice, backed by the database; guests may change settings but only for the current page session. */

import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { settingsSchema, themeSchema } from '@/schemas/settingsSchema';
import { isNotImplemented, toErrorMessage } from '@/services/api';
import * as settingsService from '@/services/settings/settingsService';
import { THEME_STORAGE_KEY } from '@/utils/constants';

import type { ModelInfo, Settings, Theme } from '@/types/settings';

export interface SettingsState {
  settings: Settings;
  models: ModelInfo[];
  /** No GET /models, so the UI only shows the running model from /health. */
  isModelListUnavailable: boolean;
  error: string | null;
}

/** Theme comes from the readable cookie so the first frame is already correct instead of flashing light. */
export function makeInitialSettingsState(): SettingsState {
  const theme = readClientAuthInfo()?.theme;

  return {
    settings: settingsSchema.parse(theme ? { theme } : {}),
    models: [],
    isModelListUnavailable: false,
    error: null,
  };
}

const settingsSlice = createSlice({
  name: 'settings',
  initialState: makeInitialSettingsState(),
  reducers: {
    /** Patches part of the settings; the API call lives in the thunk to keep this pure. */
    settingsChanged(state, action: PayloadAction<Partial<Settings>>) {
      state.settings = { ...state.settings, ...action.payload };
      state.error = null;
    },

    settingsReplaced(state, action: PayloadAction<Settings>) {
      state.settings = action.payload;
    },

    /** On sign-out, reset to defaults so the previous user's choices do not linger. */
    settingsReset(state) {
      state.settings = settingsSchema.parse({});
      state.error = null;
    },

    modelsLoaded(state, action: PayloadAction<ModelInfo[]>) {
      state.models = action.payload;
      state.isModelListUnavailable = false;
    },

    modelListUnavailable(state) {
      state.models = [];
      state.isModelListUnavailable = true;
    },

    settingsErrored(state, action: PayloadAction<string>) {
      state.error = action.payload;
    },
  },
});

export const {
  settingsChanged,
  settingsReplaced,
  settingsReset,
  modelsLoaded,
  modelListUnavailable,
  settingsErrored,
} = settingsSlice.actions;

export const settingsReducer = settingsSlice.reducer;

// --- thunk ---------------------------------------------------------------

type SettingsRootState = { settings: SettingsState; auth: { user: unknown } };

/** Applies the change immediately, then saves to the database when signed in. */
export const updateSettings = createAsyncThunk<
  void,
  Partial<Settings>,
  { state: SettingsRootState }
>('settings/update', async (patch, { dispatch, getState }) => {
  dispatch(settingsChanged(patch));

  // Guests have nowhere to save, so settings only live for this page session.
  if (!getState().auth.user) return;

  try {
    await settingsService.saveSettings(getState().settings.settings);
  } catch (caught) {
    // A missing endpoint is not the user's problem, so stay silent.
    if (!isNotImplemented(caught)) dispatch(settingsErrored(toErrorMessage(caught)));
  }
});

/** Pulls settings from the database, after sign-in and on app start. */
export const pullSettings = createAsyncThunk<void, void, { state: SettingsRootState }>(
  'settings/pull',
  async (_, { dispatch, getState }) => {
    if (!getState().auth.user) return;

    try {
      dispatch(settingsReplaced(await settingsService.fetchSettings()));
    } catch (caught) {
      if (!isNotImplemented(caught)) dispatch(settingsErrored(toErrorMessage(caught)));
    }
  },
);

export const loadModels = createAsyncThunk<void, void>(
  'settings/loadModels',
  async (_, { dispatch }) => {
    try {
      dispatch(modelsLoaded(await settingsService.fetchModels()));
    } catch (caught) {
      if (isNotImplemented(caught)) {
        dispatch(modelListUnavailable());
        return;
      }
      dispatch(settingsErrored(toErrorMessage(caught)));
    }
  },
);
