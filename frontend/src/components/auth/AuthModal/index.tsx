'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/common/Button';
import { GoogleIcon } from '@/components/common/Icon';
import { Modal } from '@/components/common/Modal';
import { Spinner } from '@/components/common/Spinner';
import { TextField } from '@/components/common/TextField';
import { useAuth } from '@/hooks/auth/useAuth';
import { loginFormSchema, registerFormSchema } from '@/schemas/authSchema';
import { googleAuthorizeUrl } from '@/utils/authUrl';

import type { FieldErrors } from '@/types/auth';

export type AuthMode = 'login' | 'register';

interface AuthModalProps {
  isOpen: boolean;
  mode: AuthMode;
  onClose: () => void;
  onModeChange: (mode: AuthMode) => void;
}

/** Login / register dialog; `key={mode}` remounts the form so its state resets without setState-in-effect. */
export function AuthModal({ isOpen, mode, onClose, onModeChange }: AuthModalProps) {
  return (
    <Modal title={mode === 'register' ? 'Tạo tài khoản' : 'Đăng nhập'} isOpen={isOpen} onClose={onClose}>
      <AuthForm key={mode} mode={mode} onSuccess={onClose} onModeChange={onModeChange} />
    </Modal>
  );
}

interface AuthFormProps {
  mode: AuthMode;
  onSuccess: () => void;
  onModeChange: (mode: AuthMode) => void;
}

const EMPTY_FORM = {
  display_name: '',
  email: '',
  password: '',
  confirm_password: '',
};

function AuthForm({ mode, onSuccess, onModeChange }: AuthFormProps) {
  const auth = useAuth();
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const isRegister = mode === 'register';
  const { clearError } = auth;

  // Clear leftover errors from the previous open; this dispatches to the store, not setState.
  useEffect(() => clearError(), [clearError]);

  const setField = (name: keyof typeof EMPTY_FORM, value: string) => {
    setForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: undefined }));
  };

  const submit = async () => {
    const schema = isRegister ? registerFormSchema : loginFormSchema;
    const parsed = schema.safeParse(form);

    if (!parsed.success) {
      setFieldErrors(collectErrors(parsed.error.issues));
      return;
    }

    const ok = isRegister
      ? await auth.register({
          email: form.email,
          password: form.password,
          display_name: form.display_name.trim(),
        })
      : await auth.login({ email: form.email, password: form.password });

    if (ok) onSuccess();
  };

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <button
        type="button"
        onClick={() => {
          // Full-page navigation, not fetch: Google blocks its consent screen in an iframe or XHR.
          window.location.href = googleAuthorizeUrl();
        }}
        className="flex w-full items-center justify-center gap-3 rounded-full border border-border-subtle px-4 py-2.5 text-sm font-medium transition hover:bg-hover"
      >
        <GoogleIcon />
        Tiếp tục với Google
      </button>

      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-border-subtle" />
        <span className="text-xs text-text-faint">hoặc</span>
        <span className="h-px flex-1 bg-border-subtle" />
      </div>

      {isRegister && (
        <TextField
          label="Tên hiển thị"
          autoComplete="name"
          placeholder="Nguyễn Văn A"
          value={form.display_name}
          error={fieldErrors.display_name}
          onChange={(event) => setField('display_name', event.target.value)}
        />
      )}

      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="ban@congty.com"
        value={form.email}
        error={fieldErrors.email}
        onChange={(event) => setField('email', event.target.value)}
      />

      <TextField
        label="Mật khẩu"
        type="password"
        autoComplete={isRegister ? 'new-password' : 'current-password'}
        placeholder="••••••••"
        value={form.password}
        error={fieldErrors.password}
        onChange={(event) => setField('password', event.target.value)}
      />

      {isRegister && (
        <TextField
          label="Nhập lại mật khẩu"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••"
          value={form.confirm_password}
          error={fieldErrors.confirm_password}
          onChange={(event) => setField('confirm_password', event.target.value)}
        />
      )}

      {auth.error && (
        <p
          role="alert"
          className={[
            'rounded-xl border px-3 py-2 text-xs leading-relaxed',
            auth.isUnavailable
              ? 'border-border-subtle text-text-muted'
              : 'border-danger/40 bg-danger/10 text-danger',
          ].join(' ')}
        >
          {auth.error}
        </p>
      )}

      <Button type="submit" disabled={auth.isBusy} className="flex w-full justify-center py-2.5">
        {auth.isBusy ? <Spinner label="Đang xử lý" /> : isRegister ? 'Tạo tài khoản' : 'Đăng nhập'}
      </Button>

      <p className="text-center text-xs text-text-muted">
        {isRegister ? 'Đã có tài khoản? ' : 'Chưa có tài khoản? '}
        <button
          type="button"
          onClick={() => onModeChange(isRegister ? 'login' : 'register')}
          className="underline underline-offset-2 hover:text-text-primary"
        >
          {isRegister ? 'Đăng nhập' : 'Đăng ký miễn phí'}
        </button>
      </p>
    </form>
  );
}

/** Collects Zod issues into a per-field map, keeping the first error for each field. */
function collectErrors(issues: { path: PropertyKey[]; message: string }[]): FieldErrors {
  const errors: FieldErrors = {};

  for (const issue of issues) {
    const key = String(issue.path[0] ?? '');
    if (key && errors[key] === undefined) errors[key] = issue.message;
  }

  return errors;
}
