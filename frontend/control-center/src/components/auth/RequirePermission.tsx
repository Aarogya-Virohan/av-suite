'use client';

import React from 'react';
import { ShieldAlert } from 'lucide-react';
import type { PlatformPermission } from '@/lib/platform-rbac';
import { useCan } from '@/store/session';

/**
 * Route-level check. The sidebar hides links the operator cannot use, but a
 * URL can be typed directly; this is the UI's last line. The backend still
 * returns 403 on its own.
 */
export function RequirePermission({ permission, children }: { permission: PlatformPermission; children: React.ReactNode }) {
  const allowed = useCan(permission);
  if (allowed) return <>{children}</>;
  return (
    <div className="mx-auto mt-10 max-w-md space-y-3 rounded-2xl border border-line bg-card p-8 text-center shadow-card">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-danger-wash text-danger">
        <ShieldAlert className="h-6 w-6" />
      </span>
      <h2 className="font-display text-lg font-bold text-ink">Access Restricted</h2>
      <p className="text-xs text-muted">Your role cannot open this page. Ask an Owner if you need it.</p>
    </div>
  );
}
