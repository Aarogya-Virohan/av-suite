/**
 * U4 (HUB-5): suspended workspace. Same file in crm, posture-tool,
 * exercise-library and psychosocial; keep the copies identical.
 *
 * The backend answers 403 {meta: {error: {code: "WORKSPACE_SUSPENDED",
 * details: {level: "clinic" | "organization"}}}} on any authed call (and at
 * login / switch-workspace) when the clinic or its organization is paused.
 * The api helper calls reportSuspended(); SuspendedScreen shows one
 * full-page screen.
 */
import { useSyncExternalStore } from 'react';
import { asset, hubLoginUrl } from './hub';

export type SuspendedLevel = 'clinic' | 'organization';

export const SUSPENDED_CODE = 'WORKSPACE_SUSPENDED';
export const SUSPENDED_TITLE = "Your clinic's access is paused. Please contact AV support.";
export const SUSPENDED_DETAIL: Record<SuspendedLevel, string> = {
  clinic: 'This clinic is paused.',
  organization: "Your organization's account is paused.",
};

let current: SuspendedLevel | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

/** Level from an error details object; anything unknown counts as clinic. */
export function suspendedLevel(details: unknown): SuspendedLevel {
  const level = (details as { level?: unknown } | null | undefined)?.level;
  return level === 'organization' ? 'organization' : 'clinic';
}

/** Clears the shared session keys and shows the suspended screen. */
export function reportSuspended(details?: unknown): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem('token');
    window.localStorage.removeItem('userEmail');
  } catch {
    // storage blocked: nothing to clear
  }
  current = suspendedLevel(details);
  emit();
}

export function clearSuspended(): void {
  current = null;
  emit();
}

export function getSuspended(): SuspendedLevel | null {
  return current;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useSuspended(): SuspendedLevel | null {
  return useSyncExternalStore(subscribe, getSuspended, () => null);
}

/** Hub login in hub mode, else this app's own /login. */
export function signInUrl(): string {
  return hubLoginUrl({}) ?? asset('/login');
}
