'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, ChevronsUpDown, Loader2, LogOut } from 'lucide-react';
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

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

/**
 * Clinic card at the foot of the sidebar, with logout (D-030). When the account
 * belongs to more than one clinic the card opens a list to switch; switching
 * gets a new token for that clinic and reloads, so no data from the previous
 * clinic stays in memory. With one clinic the card is plain text.
 */
export function WorkspaceCard({ clinicName, roleText }: { clinicName: string; roleText: string }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const activeClinicId = useAuthStore((s) => s.clinic?.id ?? s.clinicId ?? null);
  const logout = useAuthStore((s) => s.logout);
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

  const canSwitch = workspaces.length > 1;

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
      toast.error(err instanceof Error ? err.message : 'Could not switch clinic.');
      setSwitchingTo(null);
    }
  };

  const identity = (
    <>
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-lime to-fresh text-[11px] font-bold text-midnight">
        {initials(clinicName)}
      </span>
      <span className="min-w-0 flex-1 text-left">
        <span className="block truncate text-[13px] font-semibold">{clinicName}</span>
        <span className="block text-[11px] text-[#aab2d6]">{roleText}</span>
      </span>
    </>
  );

  return (
    <div ref={rootRef} className="relative">
      {open && canSwitch && (
        <ul
          role="listbox"
          aria-label="Switch clinic"
          className="absolute bottom-full left-0 right-0 z-40 mb-2 overflow-hidden rounded-xl border border-line bg-card py-1 text-ink shadow-card"
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

      <div className="flex items-center gap-1 rounded-xl border border-white/[0.07] bg-white/[0.06] p-2.5">
        {canSwitch ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-label={`Switch clinic, current: ${clinicName}`}
            className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 rounded-lg transition-colors hover:bg-white/[0.06]"
          >
            {identity}
            <ChevronsUpDown className="h-4 w-4 shrink-0 text-[#aab2d6]" />
          </button>
        ) : (
          <div className="flex min-w-0 flex-1 items-center gap-2.5">{identity}</div>
        )}
        <button
          type="button"
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
    </div>
  );
}
