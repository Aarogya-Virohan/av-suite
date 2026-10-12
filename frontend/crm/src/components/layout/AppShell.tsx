'use client';

import React from 'react';
import { SidebarNavigation } from './SidebarNavigation';
import { CommandBar } from './CommandBar';
import { AuthGuard } from '../auth/AuthGuard';
import { useUiStore, useAuthStore } from '../../store';
import { CalendarDays, Search } from 'lucide-react';
import { useClinicSettings } from '../../features/settings/api';
import { cn } from '../../lib/cn';
import { hasCapability, usePermissionSubscription } from '../../config/permissions';

const todayLabel = () =>
  new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date());

export function AppShell({ children }: { children: React.ReactNode }) {
  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen);
  usePermissionSubscription(); // Decisions.md D-013
  const clinic = useAuthStore((s) => s.clinic);
  // Staff without settings.view got a 403 on every page (L-29). The clinic
  // from login already carries the name, logo and colour.
  const { data: clinicSettings } = useClinicSettings(hasCapability('settings.view'));
  const effectiveClinic = clinic || clinicSettings;
  const [today, setToday] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (effectiveClinic?.branding_color) {
      document.documentElement.style.setProperty('--brand-navy', effectiveClinic.branding_color);
    }
  }, [effectiveClinic?.branding_color]);

  // Rendered after mount so the server and client markup match.
  React.useEffect(() => {
    setToday(todayLabel());
  }, []);

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-canvas text-ink dark:bg-slate-950 dark:text-slate-100">
        {/* Sidebar */}
        <SidebarNavigation />

        {/* Main Content Area */}
        <div
          className={cn(
            'flex min-w-0 flex-1 flex-col transition-all duration-200',
            isSidebarOpen ? 'pl-64' : 'pl-16',
          )}
        >
          {/* Top Header */}
          <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-line bg-canvas/85 px-8 backdrop-blur dark:border-slate-800 dark:bg-slate-900">
            <button
              onClick={() => {
                const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
                window.dispatchEvent(event);
              }}
              className="flex h-10 w-full max-w-[420px] cursor-pointer items-center gap-2.5 rounded-[10px] border border-line bg-card px-3 text-sm text-slate-400 transition-colors hover:border-teal-300 dark:border-slate-700 dark:bg-slate-800"
            >
              <Search className="h-4 w-4" />
              <span>Search patients or run commands…</span>
              <kbd className="ml-auto rounded-md border border-line bg-canvas px-1.5 py-0.5 font-sans text-[11px] font-semibold text-muted dark:bg-slate-700">
                ⌘K
              </kbd>
            </button>

            <div className="flex items-center gap-2.5">
              {today && (
                <span className="hidden h-10 items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-sm font-medium text-ink-2 md:flex">
                  <CalendarDays className="h-4 w-4" />
                  {today}
                </span>
              )}
              <span className="inline-flex h-10 items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-sm font-semibold text-ink-2">
                <span className="h-2 w-2 rounded-full bg-logo-teal" aria-hidden="true" />
                {effectiveClinic?.name || 'Your clinic'}
              </span>
            </div>
          </header>

          {/* Page Body */}
          <main className="flex-1 overflow-y-auto px-8 py-6">{children}</main>
        </div>

        {/* Global Cmd+K CommandBar */}
        <CommandBar />
      </div>
    </AuthGuard>
  );
}
