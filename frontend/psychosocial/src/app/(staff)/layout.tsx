'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2, Lock } from 'lucide-react';
import { api } from '@/lib/api';
import { clearStoredToken } from '@/lib/auth';
import { useTokenStatus } from '@/lib/use-token';
import type { Me } from '@/lib/types';
import { Button } from '@/components/ui/brand';
import { MeProvider, PRODUCT_KEY } from '@/components/staff/session-context';
import { StaffShell } from '@/components/staff/StaffShell';

function FullScreen({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-canvas p-6">{children}</div>;
}

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const tokenStatus = useTokenStatus();
  const ready = tokenStatus === 'valid';

  useEffect(() => {
    if (tokenStatus === 'missing') {
      clearStoredToken();
      router.replace('/login');
    }
  }, [tokenStatus, router]);

  const me = useQuery({ queryKey: ['me'], queryFn: () => api.get<Me>('/me'), enabled: ready });

  if (!ready || me.isPending) {
    return (
      <FullScreen>
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </FullScreen>
    );
  }

  if (me.isError) {
    return (
      <FullScreen>
        <div className="max-w-sm text-center">
          <p className="font-display text-lg font-bold text-ink">Could not load your account</p>
          <p className="mt-1 text-sm text-muted">{me.error.message}</p>
          <Button className="mt-5" onClick={() => me.refetch()}>
            Try again
          </Button>
        </div>
      </FullScreen>
    );
  }

  const enabled = me.data.active_products.some((p) => p.key === PRODUCT_KEY && p.status === 'enabled');
  if (!enabled) {
    return (
      <FullScreen>
        <div className="max-w-md rounded-2xl border border-line bg-card p-8 text-center shadow-card">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-warn-wash text-warn">
            <Lock className="h-5 w-5" aria-hidden="true" />
          </span>
          <h1 className="mt-4 font-display text-xl font-bold text-ink">Screening is not enabled</h1>
          <p className="mt-2 text-sm text-muted">
            Psycho-social screening is not active for {me.data.active_workspace?.name ?? 'this clinic'}. A clinic
            admin can add it from the AV Suite marketplace.
          </p>
          <Button
            variant="secondary"
            className="mt-6"
            onClick={() => {
              clearStoredToken();
              router.replace('/login');
            }}
          >
            Sign in with another account
          </Button>
        </div>
      </FullScreen>
    );
  }

  return (
    <MeProvider value={me.data}>
      <StaffShell>{children}</StaffShell>
    </MeProvider>
  );
}
