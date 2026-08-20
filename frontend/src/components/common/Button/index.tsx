import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: 'bg-accent text-accent-contrast hover:opacity-90',
  secondary: 'border border-border-subtle hover:bg-hover',
  ghost: 'text-text-muted hover:bg-hover',
  danger: 'border border-danger/40 text-danger hover:bg-danger/10',
};

const SIZE_CLASS: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
};

// Fully rounded to match ChatGPT's button style.
const BASE_CLASS =
  'rounded-full font-medium transition disabled:cursor-not-allowed disabled:opacity-40';

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[BASE_CLASS, VARIANT_CLASS[variant], SIZE_CLASS[size], className].join(' ')}
      {...props}
    />
  );
}
