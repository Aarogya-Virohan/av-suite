/** Helpers for the anonymised statistics page (SRS 4.3.3). */

/** yyyy-mm-dd in the browser's calendar. */
export function isoDay(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** The last `days` days ending today, inclusive. */
export function lastDays(days: number, today: Date = new Date()): { from: string; to: string } {
  const start = new Date(today);
  start.setDate(start.getDate() - (days - 1));
  return { from: isoDay(start), to: isoDay(today) };
}

export function statsQuery(from: string, to: string, instrument: string): string {
  const qs = new URLSearchParams({ from, to });
  if (instrument) qs.set('instrument', instrument);
  return qs.toString();
}

export function referralLine(
  r: { count: number | null; rate_percent: number | null; suppressed: boolean },
  completed: number,
): string {
  if (r.suppressed || r.count == null || r.rate_percent == null) return 'Hidden to protect a small group';
  return `${r.count} of ${completed} (${r.rate_percent}%)`;
}

/** Bar width in percent of the completed total. Hidden counts get no bar. */
export function barWidth(count: number | null, completed: number): number {
  if (count == null || completed <= 0) return 0;
  return Math.round((count / completed) * 1000) / 10;
}
