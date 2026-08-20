/** Maps raw health state to display text, shared by the header and sidebar. */

import type { HealthState } from '@/types/chat';

export type HealthTone = 'online' | 'muted' | 'danger';

export interface HealthDisplay {
  /** Primary line, usually the model name. */
  label: string;
  /** Short secondary line under the label in the sidebar. */
  detail: string;
  /** Tooltip text: longer, and says what to do about it. */
  hint: string;
  tone: HealthTone;
}

export function describeHealth(state: HealthState): HealthDisplay {
  if (state.kind === 'loading') {
    return {
      label: 'Đang kiểm tra…',
      detail: 'Kết nối backend',
      hint: 'Đang gọi /health',
      tone: 'muted',
    };
  }

  if (state.kind === 'down') {
    return {
      label: 'Mất kết nối',
      detail: 'Backend không phản hồi',
      hint: 'Không gọi được backend. Kiểm tra FastAPI đã chạy ở cổng 8000 chưa.',
      tone: 'danger',
    };
  }

  const { health } = state;

  if (!health.llm_reachable) {
    return {
      label: 'Model chưa sẵn sàng',
      detail: `Provider ${health.llm_provider}`,
      hint: `Provider "${health.llm_provider}" không phản hồi. Kiểm tra Ollama đã chạy chưa.`,
      tone: 'danger',
    };
  }

  return {
    label: health.model,
    detail: `Provider ${health.llm_provider}`,
    hint: `Provider: ${health.llm_provider} · Backend v${health.app_version}`,
    tone: 'online',
  };
}
