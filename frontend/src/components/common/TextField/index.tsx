import type { InputHTMLAttributes } from 'react';

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** Per-field error; when set the border turns red and screen readers announce it. */
  error?: string;
}

export function TextField({ label, error, id, className = '', ...props }: TextFieldProps) {
  const fieldId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`;
  const errorId = `${fieldId}-error`;

  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className="block text-sm font-medium">
        {label}
      </label>

      <input
        id={fieldId}
        aria-invalid={error !== undefined}
        aria-describedby={error ? errorId : undefined}
        className={[
          'w-full rounded-xl border bg-bg px-3 py-2 text-sm outline-none transition',
          'placeholder:text-text-faint focus:border-text-faint',
          error ? 'border-danger' : 'border-border-subtle',
          className,
        ].join(' ')}
        {...props}
      />

      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
