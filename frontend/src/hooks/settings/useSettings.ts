'use client';

/** Binds the settings store and model list to the UI. */

import { useCallback, useEffect } from 'react';

import { useAppDispatch, useAppSelector } from '@/store';
import { loadModels, updateSettings } from '@/store/settings/settingsSlice';

import type { ModelInfo, Settings, Theme } from '@/types/settings';

interface UseSettingsResult {
  settings: Settings;
  models: ModelInfo[];
  isModelListUnavailable: boolean;
  error: string | null;
  update: (patch: Partial<Settings>) => void;
  setTheme: (theme: Theme) => void;
  setModel: (model: string | null) => void;
  refreshModels: () => void;
}

export function useSettings(): UseSettingsResult {
  const dispatch = useAppDispatch();

  const settings = useAppSelector((state) => state.settings.settings);
  const models = useAppSelector((state) => state.settings.models);
  const isModelListUnavailable = useAppSelector((state) => state.settings.isModelListUnavailable);
  const error = useAppSelector((state) => state.settings.error);

  const update = useCallback(
    (patch: Partial<Settings>) => {
      void dispatch(updateSettings(patch));
    },
    [dispatch],
  );

  const refreshModels = useCallback(() => {
    void dispatch(loadModels());
  }, [dispatch]);

  // Applied to <html> for CSS to read; a global DOM effect, so it lives here, not in a screen.
  useEffect(() => {
    const root = document.documentElement;

    if (settings.theme === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', settings.theme);
    }
  }, [settings.theme]);

  return {
    settings,
    models,
    isModelListUnavailable,
    error,
    update,
    setTheme: useCallback((theme: Theme) => update({ theme }), [update]),
    setModel: useCallback((model: string | null) => update({ model }), [update]),
    refreshModels,
  };
}
