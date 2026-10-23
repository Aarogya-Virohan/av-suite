'use client';

import React from 'react';
import { SidebarNavigation } from './SidebarNavigation';
import { CommandBar } from './CommandBar';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { HeaderCalendar } from './HeaderCalendar';
import { AuthGuard } from '../auth/AuthGuard';
import { useUiStore, useAuthStore } from '../../store';
import { CalendarDays, Menu, Search } from 'lucide-react';
import { useClinicSettings } from '../../features/settings/api';
import { cn } from '../../lib/cn';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../config/permissions';

const todayLabel = () =>
  new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date());

export function AppShell({ children }: { children: React.ReactNode }) {
  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen);
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);
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
    // Phones start with the sidebar closed; it opens as an overlay from the menu button.
    if (window.matchMedia('(max-width: 767px)').matches) setSidebarOpen(false);
  }, [setSidebarOpen]);

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-canvas text-ink dark:bg-slate-950 dark:text-slate-100">
        {/* Sidebar */}
        <SidebarNavigation />
        {isSidebarOpen && (
          <div
            aria-hidden="true"
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 z-20 bg-midnight/50 backdrop-blur-xs md:hidden"
          />
        )}

        {/* Main Content Area */}
        <div
          className={cn(
            'flex min-w-0 flex-1 flex-col transition-all duration-200',
            isSidebarOpen ? 'md:pl-64' : 'md:pl-16',
          )}
        >
          {/* Top Header */}
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur md:z-20 md:gap-4 md:px-8 dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              aria-label="Open menu"
              onClick={() => setSidebarOpen(true)}
              className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-[10px] border border-line bg-card text-ink-2 transition-colors hover:border-teal-300 md:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <button
              onClick={() => {
                const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
                window.dispatchEvent(event);
              }}
              className="flex h-10 w-full max-w-[420px] cursor-pointer items-center gap-2.5 rounded-[10px] border border-line bg-card px-3 text-sm text-slate-400 transition-colors hover:border-teal-300 dark:border-slate-700 dark:bg-slate-800"
            >
              <Search className="h-4 w-4" />
              <span className="truncate">Search patients or run commands…</span>
              <kbd className="ml-auto hidden sm:inline rounded-md border border-line bg-canvas px-1.5 py-0.5 font-sans text-[11px] font-semibold text-muted dark:bg-slate-700">
                ⌘K
              </kbd>
            </button>

            <div className="flex items-center gap-2.5">
              {today && canAccessModule('appointments') && <HeaderCalendar label={today} />}
              {today && !canAccessModule('appointments') && (
                <span className="hidden h-10 items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-sm font-medium text-ink-2 md:flex">
                  <CalendarDays className="h-4 w-4" />
                  {today}
                </span>
              )}
              <WorkspaceSwitcher fallbackName={effectiveClinic?.name} />
            </div>
          </header>

          {/* Page Body */}
          <main className="flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-6">{children}</main>
        </div>

        {/* Global Cmd+K CommandBar */}
        <CommandBar />
      </div>
    </AuthGuard>
  );
}
