'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, ChevronDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '../../lib/api-client';
import { setStoredToken } from '../../lib/auth';
import { useAuthStore } from '../../store';
import { cn } from '../../lib/cn';
import { ROLE_LABEL } from '../../lib/workspaces';

interface Workspace {
  id: string;
  name: string;
  role: string;
}

/** The clinics this account belongs to (GET /api/v1/me). */
function useWorkspaces(enabled: boolean) {
  return useQuery<Workspace[]>({
    queryKey: ['platform-context', 'workspaces'],
    queryFn: async () => {
      const res = await apiClient.get('/me');
      const data = res.data?.data ?? res.data;
      return Array.isArray(data?.workspaces) ? (data.workspaces as Workspace[]) : [];
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Clinic name in the top bar. When the account belongs to more than one
 * clinic it opens a list to switch; switching gets a new token for that clinic
 * and reloads, so no data from the previous clinic stays in memory.
 */
export function WorkspaceSwitcher({ fallbackName }: { fallbackName?: string | null }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const activeClinicId = useAuthStore((s) => s.clinic?.id ?? s.clinicId ?? null);
  const { data: workspaces = [] } = useWorkspaces(isAuthenticated);
  const [open, setOpen] = React.useState(false);
  const [switchingTo, setSwitchingTo] = React.useState<string | null>(null);
  const rootRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const label = fallbackName || 'Your clinic';
  const canSwitch = workspaces.length > 1;

  const chipClass =
    'inline-flex h-10 items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-sm font-semibold text-ink-2';

  if (!canSwitch) {
    return (
      <span className={chipClass}>
        <span className="h-2 w-2 rounded-full bg-logo-teal" aria-hidden="true" />
        {label}
      </span>
    );
  }

  const switchTo = async (clinicId: string) => {
    if (clinicId === activeClinicId) {
      setOpen(false);
      return;
    }
    setSwitchingTo(clinicId);
    try {
      const res = await apiClient.post('/auth/switch-workspace', { clinic_id: clinicId });
      const token = res.data?.data?.access_token || res.data?.access_token;
      if (!token) throw new Error('Invalid response from server.');
      setStoredToken(token);
      // Full reload: cached queries belong to the old clinic.
      window.location.assign('/dashboard');
    } catch (err: unknown) {
      console.error('Workspace switch failed', err);
      toast.error(err instanceof Error ? err.message : 'Could not switch workspace.');
      setSwitchingTo(null);
    }
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(chipClass, 'cursor-pointer transition-colors hover:border-grove')}
      >
        <span className="h-2 w-2 rounded-full bg-logo-teal" aria-hidden="true" />
        {label}
        <ChevronDown className={cn('h-4 w-4 text-slate-400 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Switch workspace"
          className="absolute right-0 top-12 z-30 w-64 overflow-hidden rounded-xl border border-line bg-card py-1 shadow-card"
        >
          {workspaces.map((w) => {
            const isActive = w.id === activeClinicId;
            return (
              <li key={w.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={isActive}
                  disabled={switchingTo !== null}
                  onClick={() => switchTo(w.id)}
                  className="flex w-full cursor-pointer items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-ink">{w.name}</span>
                    <span className="block text-xs text-muted">{ROLE_LABEL[w.role] ?? w.role}</span>
                  </span>
                  {switchingTo === w.id ? (
                    <Loader2 className="h-4 w-4 animate-spin text-grove" />
                  ) : isActive ? (
                    <Check className="h-4 w-4 text-grove" />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
