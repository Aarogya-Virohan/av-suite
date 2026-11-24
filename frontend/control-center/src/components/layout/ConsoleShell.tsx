'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Building2, ChevronLeft, ChevronRight, LayoutDashboard, LogOut, Menu, ScrollText, ShieldCheck, BarChart3 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { Avatar } from '@/components/ui/brand';
import { cn } from '@/lib/cn';
import { OPERATOR_ROLE_LABEL } from '@/lib/format';
import { roleHas, type PlatformPermission } from '@/lib/platform-rbac';
import { useSession } from '@/store/session';
import { MockModeBadge } from './MockModeBadge';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  permission: PlatformPermission;
}

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Platform',
    items: [
      { label: 'Overview', href: '/overview', icon: LayoutDashboard, permission: 'platform.usage.read' },
      { label: 'Organizations', href: '/organizations', icon: Building2, permission: 'platform.organizations.read' },
      { label: 'Usage', href: '/usage', icon: BarChart3, permission: 'platform.usage.read' },
    ],
  },
  {
    label: 'Governance',
    items: [
      { label: 'Audit log', href: '/audit-logs', icon: ScrollText, permission: 'platform.audit.read' },
      { label: 'Operators', href: '/operators', icon: ShieldCheck, permission: 'platform.operators.manage' },
    ],
  },
];

/** Clinic and organization pages belong to the Organizations section. */
function isActive(pathname: string, href: string): boolean {
  if (href === '/organizations') return pathname.startsWith('/organizations') || pathname.startsWith('/clinics');
  return pathname.startsWith(href);
}

export function ConsoleShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ShellFrame>{children}</ShellFrame>
    </AuthGuard>
  );
}

function ShellFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const operator = useSession((s) => s.operator);
  const signOut = useSession((s) => s.signOut);
  // ShellFrame only mounts on the client (after AuthGuard has the session),
  // so reading the viewport here cannot cause a hydration mismatch.
  const [open, setOpen] = useState(() => typeof window === 'undefined' || !window.matchMedia('(max-width: 767px)').matches);

  const closeOnPhone = () => {
    if (window.matchMedia('(max-width: 767px)').matches) setOpen(false);
  };

  const handleSignOut = () => {
    signOut();
    queryClient.clear();
    router.replace('/login');
  };

  const sections = NAV_SECTIONS.map((s) => ({ ...s, items: s.items.filter((i) => roleHas(operator?.role, i.permission)) })).filter(
    (s) => s.items.length > 0,
  );

  return (
    <div className="flex min-h-screen bg-canvas text-ink">
      <aside
        className={cn(
          'fixed bottom-0 left-0 top-0 z-30 flex flex-col overflow-hidden bg-[var(--brand-navy)] text-white transition-all duration-200',
          open ? 'w-64 translate-x-0' : 'w-16 -translate-x-full md:translate-x-0',
        )}
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_55%_at_0%_100%,rgba(27,74,84,0.9)_0%,rgba(27,74,84,0)_60%)]"
        />
        <div className={cn('relative flex h-[72px] items-center gap-3', open ? 'px-4' : 'justify-center px-2')}>
          <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-[11px] bg-white p-1 shadow-[0_0_0_2px_rgba(78,136,143,0.5),0_4px_14px_rgba(0,0,0,0.25)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/av-logo-mark.png" alt="AV Suite" className="h-full w-full object-contain" />
          </span>
          {open && (
            <div className="min-w-0 flex-1">
              <p className="truncate font-display text-base font-bold tracking-tight">AV Suite</p>
              <p className="text-[11px] font-medium text-[#aab2d6]">Control Center</p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className={cn(
              'cursor-pointer rounded-md p-1 text-[#aab2d6] hover:bg-white/10 hover:text-white',
              !open && 'absolute -right-0 top-[76px] z-10',
            )}
            aria-label="Toggle Sidebar"
          >
            {open ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>

        <nav className={cn('relative flex-1 overflow-y-auto pb-3', open ? 'px-3' : 'px-2 pt-6')}>
          {sections.map((section) => (
            <div key={section.label}>
              {open && (
                <p className="px-3 pb-2 pt-4 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#7fb3b8]">{section.label}</p>
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(pathname, item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? 'page' : undefined}
                      onClick={closeOnPhone}
                      title={!open ? item.label : undefined}
                      className={cn(
                        'relative flex items-center gap-3 rounded-[9px] px-3 py-2.5 text-sm font-medium transition-colors',
                        active
                          ? 'bg-gradient-to-r from-lime/15 to-lime/[0.02] font-semibold text-white'
                          : 'text-[#c3c9e6] hover:bg-white/[0.07] hover:text-white',
                        !open && 'justify-center px-0',
                      )}
                    >
                      {active && (
                        <span
                          aria-hidden="true"
                          className={cn(
                            'absolute bottom-2 top-2 w-[3px] rounded-r bg-lime shadow-[0_0_12px_rgba(193,255,114,0.6)]',
                            open ? '-left-3' : '-left-2',
                          )}
                        />
                      )}
                      <Icon className={cn('h-[18px] w-[18px] shrink-0', active && 'text-lime')} strokeWidth={1.8} />
                      {open && <span>{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className={cn('relative border-t border-white/10', open ? 'p-3' : 'p-2')}>
          {open ? (
            <div className="flex items-center gap-3 rounded-xl bg-white/[0.06] p-2.5">
              <Avatar name={operator?.name} size={34} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{operator?.name}</p>
                <p className="text-[11px] text-[#aab2d6]">{operator ? OPERATOR_ROLE_LABEL[operator.role] : ''} · Super admin</p>
              </div>
              <button
                type="button"
                onClick={handleSignOut}
                className="cursor-pointer rounded-md p-1.5 text-[#ffb4a8] transition-colors hover:bg-white/10"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="h-[18px] w-[18px]" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleSignOut}
              className="flex w-full cursor-pointer justify-center rounded-[9px] py-2.5 text-[#ffb4a8] transition-colors hover:bg-white/10"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-[18px] w-[18px]" />
            </button>
          )}
        </div>
      </aside>
      {open && (
        <div aria-hidden="true" onClick={() => setOpen(false)} className="fixed inset-0 z-20 bg-midnight/50 backdrop-blur-xs md:hidden" />
      )}

      {/* Navy column behind the fixed sidebar. As a flex child it stretches to the
          full page height, so a long page never shows the sidebar ending mid-way;
          the sidebar itself stays pinned to the viewport while scrolling. */}
      <div
        aria-hidden="true"
        className={cn('hidden shrink-0 bg-[var(--brand-navy)] transition-all duration-200 md:block', open ? 'w-64' : 'w-16')}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur md:px-8">
          <button
            type="button"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
            className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-[10px] border border-line bg-card text-ink-2 transition-colors hover:border-teal-300 md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          <p className="text-sm font-semibold text-ink-2">Super admin console</p>
          <MockModeBadge />
          <div className="ml-auto flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/av-logo-wordmark.png" alt="AV Suite" className="hidden h-8 w-auto sm:block" />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-6">{children}</main>
      </div>
    </div>
  );
}
