'use client';

import React, { useState, useEffect } from 'react';
import { LogOut, Menu, Moon, RefreshCw, ShieldCheck, Sun } from 'lucide-react';
import type { NavTab } from './Sidebar';
import { formatRole } from '@/features/auth/roleAccess';
import type { AuthSession } from '@/features/auth/auth.types';

interface TopbarProps {
  activeTab: NavTab;
  onOpenMenu: () => void;
  onRefresh: () => void;
  authSession: AuthSession;
  onLogout: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  activeTab,
  onOpenMenu,
  onRefresh,
  authSession,
  onLogout
}) => {
  const [isDark, setIsDark] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [latency, setLatency] = useState<string>('');

  useEffect(() => {
    // Check initial theme
    const savedTheme = localStorage.getItem('aarogya_theme');
    if (savedTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      setIsDark(true);
    }
    updateTime();
    updateLatency();
  }, [activeTab]);

  const updateLatency = () => {
    if (typeof window !== 'undefined') {
      setLatency(localStorage.getItem('api_last_latency') || '');
    }
  };

  const updateTime = () => {
    const now = new Date();
    setLastUpdated(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  };

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('aarogya_theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('aarogya_theme', 'light');
    }
  };

  const titles: Record<NavTab, string> = {
    dashboard: 'Dashboard Overview',
    analytics: 'Clinic Analytics & Performance',
    patients: 'Patient Directory',
    appointments: 'Appointments & Booking Management',
    billing: 'Billing, Invoices & Financials',
    leads: 'Leads & Patient Pipeline',
    therapists: 'Therapist & Doctor Directory',
    recycle: 'Recycle Bin & Restoration',
    settings: 'Clinic Settings & Configuration'
  };

  const handleRefreshClick = () => {
    updateTime();
    onRefresh();
    setTimeout(updateLatency, 200);
  };

  return (
    <header className="sticky top-0 z-30 bg-[var(--card-bg)] border-b border-[var(--border)] px-6 py-4 flex items-center justify-between shadow-sm transition-colors duration-200">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMenu}
          className="md:hidden text-[var(--text-light)] hover:text-[var(--text)] p-1.5 rounded-lg border border-[var(--border)]"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-bold text-[var(--text)]">{titles[activeTab]}</h1>
      </div>

      <div className="flex items-center gap-4">
        {latency && (
          <span className="text-[10px] uppercase font-bold tracking-widest text-[var(--teal)] px-2 py-1 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            ⚡ {latency}
          </span>
        )}

        {lastUpdated && (
          <span className="hidden sm:inline-block text-xs text-[var(--text-light)] font-medium">
            Updated: {lastUpdated}
          </span>
        )}

        <div className="hidden items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--text)] lg:flex">
          <ShieldCheck className="h-3.5 w-3.5 text-[var(--teal)]" />
          <span>{formatRole(authSession.role)}</span>
          <span className="max-w-24 truncate text-[var(--text-light)]">
            {authSession.clinicId}
          </span>
        </div>

        <button
          onClick={handleRefreshClick}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg)] transition-colors hover:scale-105"
          title="Refresh Data"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg)] transition-colors"
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
        </button>

        <button
          onClick={onLogout}
          className="p-2 rounded-lg border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg)] transition-colors"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
