import type { ReactNode } from 'react';

type Tone = 'neutral' | 'danger';

interface StatusBadgeProps {
  children: ReactNode;
  tone?: Tone;
  title?: string;
}

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'text-text-muted',
  danger: 'text-danger',
};

/** Pill badge with a coloured dot, used for system status. */
export function StatusBadge({ children, tone = 'neutral', title }: StatusBadgeProps) {
  return (
    <span
      title={title}
      className={[
        'inline-flex items-center gap-2 rounded-full border border-border-subtle px-3 py-1 text-xs',
        TONE_CLASS[tone],
      ].join(' ')}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}
