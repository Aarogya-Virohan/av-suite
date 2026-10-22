import { formatDate } from './format';
import type { Schedule } from './types';

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
