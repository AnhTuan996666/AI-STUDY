import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Tone = 'default' | 'danger';
type Size = 'sm' | 'md';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: an icon-only button still needs a label for screen readers. */
  label: string;
  children: ReactNode;
  tone?: Tone;
  size?: Size;
}

const TONE_CLASS: Record<Tone, string> = {
  default: 'text-text-muted hover:bg-hover hover:text-text-primary',
  danger: 'text-text-muted hover:bg-hover hover:text-danger',
};

const SIZE_CLASS: Record<Size, string> = {
  sm: 'p-1.5',
  md: 'p-2',
};

export function IconButton({
  label,
  tone = 'default',
  size = 'md',
  className = '',
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={['rounded-lg transition', TONE_CLASS[tone], SIZE_CLASS[size], className].join(' ')}
      {...props}
    >
      {children}
    </button>
  );
}
