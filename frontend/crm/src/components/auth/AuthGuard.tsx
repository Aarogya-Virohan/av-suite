'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getAuthSession } from '@/features/auth/auth.storage';

const PUBLIC_PATHS = ['/login'];

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard - wraps protected content.
 * Reads session from sessionStorage (where JWT is persisted post-login).
 * If no valid session, redirects to /login preserving ?next= for return.
 * Renders nothing until auth check is complete to prevent flash of protected content.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
    if (isPublic) {
      setChecked(true);
      return;
    }

    const session = getAuthSession();
    if (!session) {
      const next = encodeURIComponent(pathname);
      router.replace(`/login?next=${next}`);
      return;
    }

    setChecked(true);
  }, [pathname, router]);

  if (!checked) {
    // Blank screen while checking — prevents flash of protected content
    return null;
  }

  return <>{children}</>;
}
