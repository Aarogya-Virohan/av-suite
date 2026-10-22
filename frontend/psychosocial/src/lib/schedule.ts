import { formatDate } from './format';
import type { InstrumentId, InstrumentSummary, Schedule } from './types';

/** "every 4 weeks", "every 10 days" */
export function intervalWords(days: number): string {
  if (days % 7 === 0) {
    const weeks = days / 7;
    return weeks === 1 ? 'every week' : `every ${weeks} weeks`;
  }
  return `every ${days} days`;
}

/** What the clinic should know about a repeat right now. */
export function scheduleStatus(s: Schedule): string {
  switch (s.state) {
    case 'due':
      return `Due since ${formatDate(s.next_due_at)}`;
    case 'upcoming':
      return `Next due ${formatDate(s.next_due_at)}`;
    case 'waiting':
      return 'Link sent, waiting for the patient';
    default:
      return 'Paused: the patient withdrew consent';
  }
}

export const REPEAT_OPTIONS: { weeks: number | null; label: string }[] = [
  { weeks: null, label: 'Just once' },
  { weeks: 2, label: 'Every 2 weeks' },
  { weeks: 4, label: 'Every 4 weeks' },
  { weeks: 6, label: 'Every 6 weeks' },
  { weeks: 8, label: 'Every 8 weeks' },
  { weeks: 12, label: 'Every 12 weeks' },
];

/** Repeat choices, plus a stored value the standard list does not have (e.g. 3 weeks). */
export function repeatOptionsWith(weeks: number | null | undefined): { weeks: number | null; label: string }[] {
  if (weeks == null || REPEAT_OPTIONS.some((o) => o.weeks === weeks)) return REPEAT_OPTIONS;
  return [...REPEAT_OPTIONS, { weeks, label: weeks === 1 ? 'Every week' : `Every ${weeks} weeks` }].sort(
    (a, b) => (a.weeks ?? 0) - (b.weeks ?? 0),
  );
}

export interface ClinicDefault {
  /** Weeks to prefill, null = just once. */
  weeks: number | null;
  /** The ticked screeners have different clinic defaults, so nothing is prefilled. */
  mixed: boolean;
  /** One line for the form, or null when no clinic default applies. */
  hint: string | null;
}

function words(weeks: number | null): string {
  return weeks == null ? 'just once' : intervalWords(weeks * 7);
}

/**
 * What the Repeat field starts at for the ticked screeners (SRS 4.3.2).
 * One link has one repeat, so a default is used only when every ticked
 * screener shares it. Sending with a repeat replaces a running repeat's
 * interval, so a screener that already repeats for this patient (`running`,
 * instrument id -> interval in days) never gets the clinic default: the form
 * starts at Just once, which leaves that repeat as it is.
 */
export function clinicDefaultRepeat(
  selected: InstrumentId[],
  instruments: InstrumentSummary[],
  running: Partial<Record<InstrumentId, number>> = {},
): ClinicDefault {
  const picked = selected
    .map((id) => instruments.find((i) => i.id === id))
    .filter((i): i is InstrumentSummary => Boolean(i));
  const repeating = picked.filter((i) => running[i.id] != null);
  if (repeating.length > 0) {
    const parts = repeating.map((i) => `${i.short_name} ${intervalWords(running[i.id]!)}`).join(', ');
    const one = repeating.length === 1;
    return {
      weeks: null,
      mixed: false,
      hint: `Already repeating for this patient: ${parts}. Just once keeps ${one ? 'that repeat' : 'those repeats'} as ${one ? 'it is' : 'they are'}.`,
    };
  }
  if (picked.length === 0 || picked.every((i) => i.default_repeat_weeks == null)) {
    return { weeks: null, mixed: false, hint: null };
  }
  const values = new Set(picked.map((i) => i.default_repeat_weeks ?? null));
  if (values.size === 1) {
    const weeks = picked[0].default_repeat_weeks ?? null;
    const names = picked.map((i) => i.short_name).join(' and ');
    return { weeks, mixed: false, hint: `Clinic default for ${names}: ${words(weeks)}.` };
  }
  const parts = picked.map((i) => `${i.short_name} ${words(i.default_repeat_weeks ?? null)}`).join(', ');
  return { weeks: null, mixed: true, hint: `Clinic defaults differ (${parts}). Choose one for this link.` };
}
