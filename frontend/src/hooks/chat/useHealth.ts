'use client';

/** Polls backend health for the indicators in the header and sidebar. */

import { useEffect, useState } from 'react';

import { fetchHealth } from '@/services/chat/chatService';
import { HEALTH_POLL_INTERVAL_MS } from '@/utils/constants';

import type { HealthState } from '@/types/chat';

export function useHealth(intervalMs = HEALTH_POLL_INTERVAL_MS): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();

    const check = async () => {
      try {
        const health = await fetchHealth(controller.signal);
        setState({ kind: 'ok', health });
      } catch {
        if (!controller.signal.aborted) setState({ kind: 'down' });
      }
    };

    void check();
    const timer = setInterval(() => void check(), intervalMs);

    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [intervalMs]);

  return state;
}
