import type { BadgeTone } from '@/components/ui/brand';
import type { Entitlement, EntitlementStatus } from '@/lib/platform-api/types';

/*
 * Validity in the console is picked as calendar days in India time.
 *
 * - valid_from: access starts at 00:00 IST on that day.
 * - valid_until (UI): access lasts THROUGH that day. The backend stores an
 *   exclusive bound (6.1: valid_until <= now means expired), so the console
 *   sends the next day 00:00 IST and shows the stored value minus one day.
 */
const IST = 'Asia/Kolkata';
const IST_OFFSET = '+05:30';
const DAY_MS = 24 * 60 * 60 * 1000;

function istDay(ms: number): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: IST, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(ms));
}

/** "2026-12-10" -> 00:00 IST that day. */
export function fromDateToIso(value: string): string | null {
  if (!value) return null;
  return new Date(`${value}T00:00:00${IST_OFFSET}`).toISOString();
}

/** "2026-12-10" (last day with access) -> 00:00 IST on 2026-12-11 (exclusive bound). */
export function untilDateToIso(value: string): string | null {
  if (!value) return null;
  return new Date(Date.parse(`${value}T00:00:00${IST_OFFSET}`) + DAY_MS).toISOString();
}

export function isoToFromDate(value: string | null): string {
  return value ? istDay(Date.parse(value)) : '';
}

/** Stored exclusive bound -> last day with access (the IST day of the last millisecond). */
export function isoToUntilDate(value: string | null): string {
  return value ? istDay(Date.parse(value) - 1) : '';
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
