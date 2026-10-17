'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Calendar,
  BarChart3,
  CreditCard,
  UserPlus,
  Stethoscope,
  Trash2,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react';
import { useAuthStore, useUiStore } from '../../store';
import { canAccessModule, hasCapability, ModuleVisibility, usePermissionSubscription } from '../../config/permissions';
import { useClinicSettings } from '../../features/settings/api';
import { cn } from '../../lib/cn';

interface NavItem {
  label: string;
  href: string;
  moduleKey: keyof ModuleVisibility;
  icon: React.ElementType;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

// Same items, routes and permission keys as before, grouped into sections.
const NAV_SECTIONS: NavSection[] = [
  {
    label: 'Clinic',
    items: [
      { label: 'Dashboard', href: '/dashboard', moduleKey: 'dashboard', icon: LayoutDashboard },
      { label: 'Patients', href: '/patients', moduleKey: 'patients', icon: Users },
      { label: 'Appointments', href: '/appointments', moduleKey: 'appointments', icon: Calendar },
      { label: 'Leads', href: '/leads', moduleKey: 'leads', icon: UserPlus },
      { label: 'Billing', href: '/billing', moduleKey: 'billing', icon: CreditCard },
      { label: 'Analytics', href: '/analytics', moduleKey: 'analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'Manage',
    items: [
      { label: 'Therapists', href: '/therapists', moduleKey: 'therapists', icon: Stethoscope },
      { label: 'Recycle Bin', href: '/recycle-bin', moduleKey: 'recycleBin', icon: Trash2 },
      { label: 'Settings', href: '/settings', moduleKey: 'settings', icon: Settings },
    ],
  },
];

function roleLabel(role: string | null | undefined): string {
  if (!role) return 'Member';
  return role.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function SidebarNavigation() {
  usePermissionSubscription(); // see Decisions.md D-013
  const pathname = usePathname();
  const role = useAuthStore((s) => s.role);
  const clinic = useAuthStore((s) => s.clinic);
  const logout = useAuthStore((s) => s.logout);
  const { isSidebarOpen, toggleSidebar } = useUiStore();
  const { data: clinicSettings } = useClinicSettings(hasCapability('settings.view')); // L-29

  const effectiveClinic = clinic || clinicSettings;
  const clinicName = effectiveClinic?.name || 'Your clinic';
  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => canAccessModule(item.moduleKey)),
  })).filter((section) => section.items.length > 0);

  return (
    <aside
      className={cn(
        'fixed bottom-0 left-0 top-0 z-30 flex flex-col overflow-hidden bg-[var(--brand-navy)] text-white transition-all duration-200',
        isSidebarOpen ? 'w-64' : 'w-16',
      )}
    >
      {/* Brand glow, taken from the website banner. Sits above the clinic's
          branding colour so a custom colour still shows through. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_55%_at_0%_100%,rgba(27,74,84,0.9)_0%,rgba(27,74,84,0)_60%)]"
      />

      {/* Header / Logo */}
      <div className={cn('relative flex h-[72px] items-center gap-3', isSidebarOpen ? 'px-4' : 'justify-center px-2')}>
        <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-[11px] bg-white p-1 shadow-[0_0_0_2px_rgba(78,136,143,0.5),0_4px_14px_rgba(0,0,0,0.25)]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={effectiveClinic?.branding_logo_url || '/brand/av-logo-mark.png'}
            alt={effectiveClinic?.branding_logo_url ? 'Clinic logo' : 'AV Suite'}
            className="h-full w-full object-contain"
          />
        </span>
        {isSidebarOpen && (
          <div className="min-w-0 flex-1">
            <p className="truncate font-display text-base font-bold tracking-tight">AV Suite</p>
            <p className="text-[11px] font-medium text-[#aab2d6]">Clinic CRM</p>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className={cn(
            'cursor-pointer rounded-md p-1 text-[#aab2d6] hover:bg-white/10 hover:text-white',
            !isSidebarOpen && 'absolute -right-0 top-[76px]',
          )}
          aria-label="Toggle Sidebar"
        >
          {isSidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav List */}
      <nav className={cn('relative flex-1 overflow-y-auto pb-3', isSidebarOpen ? 'px-3' : 'px-2 pt-6')}>
        {sections.map((section) => (
          <div key={section.label}>
            {isSidebarOpen && (
              <p className="px-3 pb-2 pt-4 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#7fb3b8]">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? 'page' : undefined}
                    className={cn(
                      'relative flex items-center gap-3 rounded-[9px] px-3 py-2.5 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-gradient-to-r from-lime/15 to-lime/[0.02] font-semibold text-white'
                        : 'text-[#c3c9e6] hover:bg-white/[0.07] hover:text-white',
                      !isSidebarOpen && 'justify-center px-0',
                    )}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className={cn(
                          'absolute bottom-2 top-2 w-[3px] rounded-r bg-lime shadow-[0_0_12px_rgba(193,255,114,0.6)]',
                          isSidebarOpen ? '-left-3' : '-left-2',
                        )}
                      />
                    )}
                    <Icon className={cn('h-[18px] w-[18px] shrink-0', isActive && 'text-lime')} strokeWidth={1.8} />
                    {isSidebarOpen && <span>{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Workspace + Logout */}
      <div className={cn('relative border-t border-white/10', isSidebarOpen ? 'p-3' : 'p-2')}>
        {isSidebarOpen ? (
          <div className="flex items-center gap-2.5 rounded-xl border border-white/[0.07] bg-white/[0.06] p-2.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-lime to-fresh text-[11px] font-bold text-midnight">
              {clinicName
                .split(/\s+/)
                .slice(0, 2)
                .map((w: string) => w[0])
                .join('')
                .toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold">{clinicName}</p>
              <p className="text-[11px] text-[#aab2d6]">{roleLabel(role)}</p>
            </div>
            <button
              onClick={() => {
                logout();
                window.location.replace('/login');
              }}
              className="cursor-pointer rounded-md p-1.5 text-[#aab2d6] transition-colors hover:bg-white/10 hover:text-[#ffb4a8]"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => {
              logout();
              window.location.replace('/login');
            }}
            className="flex w-full cursor-pointer justify-center rounded-[9px] py-2.5 text-[#ffb4a8] transition-colors hover:bg-white/10"
            title="Logout"
            aria-label="Logout"
          >
            <LogOut className="h-[18px] w-[18px]" />
          </button>
        )}
      </div>
    </aside>
  );
}
