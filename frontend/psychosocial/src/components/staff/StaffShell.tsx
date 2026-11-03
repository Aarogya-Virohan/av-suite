'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { BarChart3, ClipboardList, LogOut, Menu, ShieldCheck, SlidersHorizontal, Users, X } from 'lucide-react';
import { clearStoredToken } from '@/lib/auth';
import { cn } from '@/lib/cn';
import { Avatar } from '@/components/ui/brand';
import { useMe } from './session-context';

const NAV = [
  { href: '/sessions', label: 'Screenings', icon: ClipboardList, capability: 'screening.view' },
  { href: '/patients', label: 'Patients', icon: Users, capability: 'patients.view' },
  { href: '/access', label: 'Access', icon: ShieldCheck, capability: 'permissions.edit' },
  { href: '/reports', label: 'Reports', icon: BarChart3, capability: 'screening.aggregates' },
  { href: '/settings', label: 'Settings', icon: SlidersHorizontal, capability: 'screening.configure' },
] as const;

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const me = useMe();
  return (
    <nav aria-label="Main" className="space-y-1">
      {NAV.filter((n) => me.capabilities.includes(n.capability)).map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-semibold transition-colors',
              active ? 'bg-white/10 text-white' : 'text-[#b9c0e0] hover:bg-white/5 hover:text-white',
            )}
          >
            <Icon className={cn('h-[18px] w-[18px]', active ? 'text-lime' : '')} strokeWidth={1.8} aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  const me = useMe();
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-[11px] bg-white p-1.5 shadow-[0_0_0_2px_rgba(78,136,143,0.5)]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
      </span>
      <div className="min-w-0">
        <p className="font-display text-[15px] font-bold leading-tight tracking-tight text-white">Screening</p>
        <p className="truncate text-xs text-[#aab2d6]">{me.active_workspace?.name ?? 'AV Suite'}</p>
      </div>
    </div>
  );
}

function UserFooter() {
  const me = useMe();
  const router = useRouter();
  return (
    <div className="flex items-center gap-3 border-t border-white/10 pt-4">
      <Avatar name={me.user.name} size={34} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white">{me.user.name}</p>
        <p className="truncate text-xs capitalize text-[#aab2d6]">{me.user.role.replace('_', ' ')}</p>
      </div>
      <button
        type="button"
        onClick={() => {
          clearStoredToken();
          router.replace('/login');
        }}
        className="grid h-9 w-9 cursor-pointer place-items-center rounded-lg text-[#b9c0e0] transition-colors hover:bg-white/10 hover:text-white"
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

export function StaffShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-card px-3 py-2 text-sm font-semibold text-ink focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen flex-col justify-between bg-midnight p-5 lg:flex">
        <div className="space-y-8">
          <Brand />
          <NavLinks />
        </div>
        <UserFooter />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between bg-midnight px-4 py-3 lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="grid h-11 w-11 cursor-pointer place-items-center rounded-lg text-white hover:bg-white/10"
          aria-label="Open menu"
          aria-expanded={open}
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>
      {open ? (
        <div className="fixed inset-0 z-40 bg-midnight/55 lg:hidden" onClick={() => setOpen(false)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            className="animate-slide-in-right ml-auto flex h-full w-[82%] max-w-xs flex-col justify-between bg-midnight p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-8">
              <div className="flex items-start justify-between gap-2">
                <Brand />
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="grid h-11 w-11 cursor-pointer place-items-center rounded-lg text-white hover:bg-white/10"
                  aria-label="Close menu"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <NavLinks onNavigate={() => setOpen(false)} />
            </div>
            <UserFooter />
          </div>
        </div>
      ) : null}

      <main id="main" className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
