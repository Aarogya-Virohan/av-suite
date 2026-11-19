'use client';

import { create } from 'zustand';
import type { Operator } from '@/lib/platform-api/types';
import { roleHas, type PlatformPermission } from '@/lib/platform-rbac';

/*
 * Operator session. The token lives in sessionStorage (one tab, gone when
 * the tab closes) because this console has platform-wide power.
 * confirm in S2/U5: an httpOnly cookie would be stronger if the backend sets one.
 */
const STORAGE_KEY = 'av-control-center.session';

interface StoredSession {
  token: string;
  operator: Operator;
  expiresAt: number;
}

interface SessionState {
  token: string | null;
  operator: Operator | null;
  expiresAt: number | null;
  hydrated: boolean;
  hydrate: () => void;
  signIn: (token: string, operator: Operator, expiresInSeconds: number) => void;
  signOut: () => void;
}

function readStored(): StoredSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    if (!parsed.token || !parsed.operator || parsed.expiresAt <= Date.now()) return null;
    return parsed;
  } catch {
    return null;
  }
}

export const useSession = create<SessionState>((set) => ({
  token: null,
  operator: null,
  expiresAt: null,
  hydrated: false,
  hydrate: () => {
    const stored = readStored();
    set({ token: stored?.token ?? null, operator: stored?.operator ?? null, expiresAt: stored?.expiresAt ?? null, hydrated: true });
  },
  signIn: (token, operator, expiresInSeconds) => {
    const expiresAt = Date.now() + expiresInSeconds * 1000;
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token, operator, expiresAt } satisfies StoredSession));
    } catch {
      // Storage can be blocked; the session then lasts for this page only.
    }
    set({ token, operator, expiresAt, hydrated: true });
  },
  signOut: () => {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    set({ token: null, operator: null, expiresAt: null });
  },
}));

export function getAccessToken(): string | null {
  const { token, expiresAt } = useSession.getState();
  if (!token || !expiresAt || expiresAt <= Date.now()) return null;
  return token;
}

/** Called by the HTTP adapter on any 401: drop the session, AuthGuard sends to /login. */
export function handleUnauthorized(): void {
  useSession.getState().signOut();
}

/** UI permission check for the signed-in operator. */
export function useCan(permission: PlatformPermission): boolean {
  return useSession((s) => roleHas(s.operator?.role, permission));
}
