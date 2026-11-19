'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useSession } from '@/store/session';

/** Sends anyone without a platform session to /login. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrated = useSession((s) => s.hydrated);
  const token = useSession((s) => s.token);
  const expiresAt = useSession((s) => s.expiresAt);
  const signOut = useSession((s) => s.signOut);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace('/login');
      return;
    }
    // Leave when the 8-hour token runs out, even if the tab stays open.
    const remaining = (expiresAt ?? 0) - Date.now();
    if (remaining <= 0) {
      signOut();
      return;
    }
    const timer = window.setTimeout(signOut, Math.min(remaining, 2 ** 31 - 1));
    return () => window.clearTimeout(timer);
  }, [hydrated, token, expiresAt, router, signOut]);

  if (!hydrated || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </div>
    );
  }
  return <>{children}</>;
}
