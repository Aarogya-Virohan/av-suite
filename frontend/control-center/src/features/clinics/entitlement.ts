import type { BadgeTone } from '@/components/ui/brand';
import type { Entitlement, EntitlementStatus } from '@/lib/platform-api/types';

/*
 * Validity dates are picked as calendar days in India time. A day maps to
 * 00:00 IST of that day; valid_until is exclusive, the backend rule (6.1).
 */
const IST_OFFSET = '+05:30';

export function dateInputToIso(value: string): string | null {
  if (!value) return null;
  return new Date(`${value}T00:00:00${IST_OFFSET}`).toISOString();
}

export function isoToDateInput(value: string | null): string {
  if (!value) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(value),
  );
}

export type AccessState = 'not_granted' | 'active' | 'scheduled' | 'expired' | 'disabled';

/** Same rule as the backend's validity filter: enabled and inside [valid_from, valid_until). */
export function accessState(
  e: Pick<Entitlement, 'status' | 'valid_from' | 'valid_until'> | null | undefined,
  now: number = Date.now(),
): AccessState {
  if (!e) return 'not_granted';
  if (e.status !== 'enabled') return 'disabled';
  if (e.valid_from && Date.parse(e.valid_from) > now) return 'scheduled';
  if (e.valid_until && Date.parse(e.valid_until) <= now) return 'expired';
  return 'active';
}

export const ACCESS_LABEL: Record<AccessState, string> = {
  not_granted: 'Not granted',
  active: 'Active',
  scheduled: 'Starts later',
  expired: 'Expired',
  disabled: 'Disabled',
};

export const ACCESS_TONE: Record<AccessState, BadgeTone> = {
  not_granted: 'neutral',
  active: 'ok',
  scheduled: 'info',
  expired: 'warn',
  disabled: 'neutral',
};

export const ENTITLEMENT_STATUS_LABEL: Record<EntitlementStatus, string> = { enabled: 'Enabled', disabled: 'Disabled' };
