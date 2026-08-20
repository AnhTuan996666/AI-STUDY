'use client';

import { useState, type ReactNode } from 'react';
import { Provider } from 'react-redux';

import { makeStore } from '@/store';

/** Lazy initializer keeps one store per mount: re-renders never rebuild it, and each SSR request gets its own. */
export function StoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState(makeStore);

  return <Provider store={store}>{children}</Provider>;
}
