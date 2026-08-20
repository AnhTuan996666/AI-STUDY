import { Suspense } from 'react';

import { AuthCallback } from '@/components/auth/AuthCallback';

/** Where Google (via the backend) returns the user; the session cookie is already set, so this only confirms it. */
export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackShell message="Đang hoàn tất đăng nhập…" />}>
      <AuthCallback />
    </Suspense>
  );
}

function CallbackShell({ message }: { message: string }) {
  return (
    <main className="flex h-dvh items-center justify-center px-6 text-center">
      <p className="text-sm text-text-muted">{message}</p>
    </main>
  );
}
