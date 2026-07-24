'use client';

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/cookieAuth';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean>(false);
  const [checking, setChecking] = useState<boolean>(true);

  useEffect(() => {
    const isPublicRoute = pathname === '/login';
    const token = getAuthToken() || (typeof window !== 'undefined' ? localStorage.getItem('token') : null);

    if (!token && !isPublicRoute) {
      setAuthorized(false);
      setChecking(false);
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      } else {
        router.push('/login');
      }
    } else if (token && isPublicRoute) {
      setAuthorized(true);
      setChecking(false);
      if (typeof window !== 'undefined') {
        window.location.href = '/';
      } else {
        router.push('/');
      }
    } else {
      setAuthorized(true);
      setChecking(false);
    }
  }, [pathname, router]);

  if (checking) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-slate-900 text-slate-400 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        <span className="text-sm font-medium">Verifying Session...</span>
      </div>
    );
  }

  // Prevent rendering protected content if unauthenticated
  if (!authorized && pathname !== '/login') {
    return null;
  }

  return <>{children}</>;
};

export default AuthGuard;
