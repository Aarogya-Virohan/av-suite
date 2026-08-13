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
 */
export function AccessRestricted({ message = 'You do not have permission to access this page.' }: AccessRestrictedProps) {
  return (
    <AppShell>
      <div className="p-8 max-w-md mx-auto text-center space-y-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
        <ShieldAlert className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Access Restricted</h2>
        <p className="text-xs text-slate-500">{message}</p>
      </div>
    </AppShell>
  );
}
