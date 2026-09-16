'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getStoredToken, isTokenExpired } from '../../lib/auth';
import { useAuthStore } from '../../store';
import { Loader2 } from 'lucide-react';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const token = getStoredToken();

    if (!token || isTokenExpired(token)) {
      useAuthStore.getState().logout();
      router.replace('/login');
      return;
    }

    setToken(token);
    setIsChecking(false);
  }, [router, setToken]);

  if (isChecking && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="flex items-center gap-3 text-teal-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-sm font-medium">Verifying authentication...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
