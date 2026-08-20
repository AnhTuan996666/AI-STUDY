'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { useAuth } from '@/hooks/auth/useAuth';

/**
 * Final step of Google OAuth: the backend redirected here with the token in the query
 * string. Adopt it, load the user, then return to chat — and scrub the token from the
 * URL so it does not linger in history.
 */
export function AuthCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const { adopt } = useAuth();

  const [failure, setFailure] = useState<string | null>(params.get('error'));

  useEffect(() => {
    if (params.get('error')) return;

    const token = params.get('access_token');
    if (!token) {
      setFailure('Thiếu thông tin đăng nhập trả về từ Google. Hãy thử lại.');
      return;
    }

    const expiresInRaw = params.get('expires_in');
    const expiresIn = expiresInRaw ? Number(expiresInRaw) : null;
    const expiresAt = expiresIn && !Number.isNaN(expiresIn) ? Date.now() + expiresIn * 1000 : null;

    let cancelled = false;

    void adopt({ token, expiresAt }).then((ok) => {
      if (cancelled) return;

      if (ok) {
        // Thay vì để token nằm trong URL, chuyển về trang chat sạch.
        router.replace('/');
      } else {
        setFailure('Không xác nhận được phiên đăng nhập. Hãy thử đăng nhập lại.');
      }
    });

    return () => {
      cancelled = true;
    };
  }, [params, adopt, router]);

  return (
    <main className="flex h-dvh items-center justify-center px-6">
      <div className="w-full max-w-sm text-center">
        {failure === null ? (
          <>
            <div className="flex justify-center">
              <Spinner label="Đang hoàn tất đăng nhập" />
            </div>
            <p className="mt-4 text-sm text-text-muted">Đang hoàn tất đăng nhập…</p>
          </>
        ) : (
          <>
            <h1 className="text-lg font-semibold">Đăng nhập không thành công</h1>
            <p className="mt-2 text-sm leading-relaxed text-text-muted">{failure}</p>
            <Button onClick={() => router.replace('/')} className="mt-5 px-5">
              Về trang chat
            </Button>
          </>
        )}
      </div>
    </main>
  );
}
