'use client';

import type { ReactNode } from 'react';

interface EmptyStateProps {
  /** The composer, slotted between the heading and the suggestions like ChatGPT does. */
  children: ReactNode;
  /** Picking a suggestion sends it straight away rather than filling the input. */
  onPick: (prompt: string) => void;
  /** Can be turned off in Settings. */
  showSuggestions: boolean;
}

const SUGGESTIONS = [
  'Giải thích REST API trong 3 câu',
  'Viết hàm Python đọc file CSV',
  'So sánh SQL và NoSQL bằng bảng',
  'Tóm tắt ưu nhược điểm của self-host model',
];

/** Welcome screen shown while the conversation has no messages. */
export function EmptyState({ children, onPick, showSuggestions }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-20">
      <h1 className="mb-7 text-center text-[28px] font-semibold tracking-[-0.01em]">
        Tôi có thể giúp gì cho bạn?
      </h1>

      {children}

      <ul
        className={[
          'mt-5 flex max-w-3xl flex-wrap justify-center gap-2',
          showSuggestions ? '' : 'hidden',
        ].join(' ')}
      >
        {SUGGESTIONS.map((suggestion) => (
          <li key={suggestion}>
            <button
              type="button"
              onClick={() => onPick(suggestion)}
              className="rounded-full border border-border-subtle px-4 py-2 text-sm text-text-muted transition hover:bg-hover"
            >
              {suggestion}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
