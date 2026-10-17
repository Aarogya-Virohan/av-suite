'use client';

import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { AppShell } from '../layout/AppShell';

interface AccessRestrictedProps {
  message?: string;
}

/**
 * Renders a full-page "Access Restricted" block inside the app shell.
 * Used for route-level RBAC enforcement on routed pages.
 * Sidebar hides nav items, but with real Next.js routes a user can type
 * a URL directly — this component is the last line of defence.
 * It renders its own AppShell, so callers must not wrap it in another one.
 */
export function AccessRestricted({ message = 'You do not have permission to access this page.' }: AccessRestrictedProps) {
  return (
    <AppShell>
      <div className="mx-auto max-w-md space-y-3 rounded-2xl border border-line bg-card p-8 text-center shadow-[0_1px_2px_rgba(11,18,56,0.04)]">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-danger-wash text-danger">
          <ShieldAlert className="h-6 w-6" />
        </span>
        <h2 className="font-display text-lg font-bold text-ink">Access Restricted</h2>
        <p className="text-xs text-muted">{message}</p>
      </div>
    </AppShell>
  );
}
