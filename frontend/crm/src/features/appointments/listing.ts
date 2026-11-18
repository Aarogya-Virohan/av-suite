import type { Appointment } from '../../types/api';

/*
 * Appointment lists are filtered, ordered and counted by the server (D-028).
 * The API reads dates as India days. Before this, every screen loaded the
 * first N appointments with no date, and the server returns the oldest
 * first, so a clinic with more than N appointments saw only old ones:
 * Appointments (500), Dashboard (50), the double-booking warning (100).
 */

export type AppointmentListView = 'upcoming' | 'past' | 'day';
export type AppointmentStatusFilter = 'all' | 'scheduled' | 'completed' | 'cancelled' | 'no_show';

export interface AppointmentListQuery {
  date?: string;
  start_date?: string;
  end_date?: string;
  status?: Exclude<AppointmentStatusFilter, 'all'>;
  therapist?: string;
  order?: 'asc' | 'desc';
  offset: number;
  limit: number;
}

export const APPOINTMENTS_PAGE_SIZE = 50;
/** Backend maximum per request; one day of one clinic stays far below it. */
export const APPOINTMENTS_DAY_LIMIT = 500;

/** YYYY-MM-DD plus n calendar days (no time zone involved). */
export function addDays(isoDate: string, n: number): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + n));
  return date.toISOString().slice(0, 10);
}

/**
 * Server query for the Appointments page.
 * - upcoming: from today on, soonest first
 * - past: up to yesterday, newest first
 * - day: one India day, earliest first, not paged
 */
export function appointmentListQuery(opts: {
  view: AppointmentListView;
  today: string;
  day?: string | null;
  status: AppointmentStatusFilter;
  page: number;
  pageSize?: number;
}): AppointmentListQuery {
  const pageSize = opts.pageSize ?? APPOINTMENTS_PAGE_SIZE;
  const status = opts.status === 'all' ? undefined : opts.status;
  if (opts.view === 'day' && opts.day) {
    return { date: opts.day, status, order: 'asc', offset: 0, limit: APPOINTMENTS_DAY_LIMIT };
  }
  const offset = Math.max(0, opts.page - 1) * pageSize;
  if (opts.view === 'past') {
    return { end_date: addDays(opts.today, -1), status, order: 'desc', offset, limit: pageSize };
  }
  return { start_date: opts.today, status, order: 'asc', offset, limit: pageSize };
}

/** "1-50 of 523" text and page count for the pager. */
export function pageInfo(page: number, pageSize: number, total: number, shown: number) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = total === 0 ? 0 : (page - 1) * pageSize + shown;
  return { pages, first, last };
}

/**
 * Dashboard card: upcoming appointments first (soonest at the top), then the
 * most recent past ones. The two server lists can share today's earlier
 * appointments, so rows are de-duplicated by id.
 */
export function orderForDashboard(lists: Appointment[][], now: number = Date.now(), max = 7): Appointment[] {
  const byId = new Map<string, Appointment>();
  for (const list of lists) for (const a of list) byId.set(a.id, a);
  const items = [...byId.values()];
  const time = (a: Appointment) => new Date(a.scheduled_at).getTime();
  const upcoming = items.filter((a) => time(a) >= now).sort((a, b) => time(a) - time(b));
  const past = items.filter((a) => time(a) < now).sort((a, b) => time(b) - time(a));
  return [...upcoming, ...past].slice(0, max);
}

/**
 * Soft double-booking warning: true when [start, start + duration) overlaps
 * another active appointment of the same therapist. The old check compared
 * start times against the existing appointment's length only, so a long new
 * visit that began before another one was not caught.
 */
export function overlapsExisting(
  existing: Pick<Appointment, 'therapist_id' | 'status' | 'scheduled_at' | 'duration_minutes'>[],
  therapistId: string,
  startISO: string,
  durationMinutes: number,
): boolean {
  const start = new Date(startISO).getTime();
  if (!therapistId || Number.isNaN(start)) return false;
  const end = start + Math.max(1, durationMinutes || 30) * 60_000;
  return existing.some((apt) => {
    if (apt.therapist_id !== therapistId || apt.status === 'cancelled' || apt.status === 'no_show') return false;
    const s = new Date(apt.scheduled_at).getTime();
    const e = s + Math.max(1, apt.duration_minutes || 30) * 60_000;
    return start < e && s < end;
  });
}

/** "1 Nov", or "25 Jan 2025" when the year is not the current one. */
export function appointmentDayLabel(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  const sameYear = date.getFullYear() === now.getFullYear();
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
  }).format(date);
}
