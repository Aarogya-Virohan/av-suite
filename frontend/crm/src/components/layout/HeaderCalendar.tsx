'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';
import { localToday } from '../../lib/datetime';
import { cn } from '../../lib/cn';

const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const monthTitle = new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' });

/** Days of the month grid, Monday first, with leading blanks. */
function monthCells(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1);
  const lead = (first.getDay() + 6) % 7;
  const days = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = Array.from({ length: lead }, () => null);
  for (let d = 1; d <= days; d++) cells.push(new Date(year, month, d));
  return cells;
}

/*
 * The header date used to be plain text. Founders expected it to open a
 * calendar for scheduling (feedback C-01). Picking a day opens Appointments
 * for that day, where a visit can be booked.
 */
export function HeaderCalendar({ label }: { label: string }) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [view, setView] = React.useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const ref = React.useRef<HTMLDivElement>(null);
  const today = localToday();

  React.useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const shift = (delta: number) =>
    setView((v) => {
      const d = new Date(v.year, v.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });

  const pick = (day: Date) => {
    setOpen(false);
    router.push(`/appointments?date=${localToday(day)}`);
  };

  return (
    <div ref={ref} className="relative hidden md:block">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => {
          if (!open) {
            const now = new Date();
            setView({ year: now.getFullYear(), month: now.getMonth() });
          }
          setOpen((o) => !o);
        }}
        className="flex h-10 cursor-pointer items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-sm font-medium text-ink-2 transition-colors hover:border-teal-300 hover:text-ink dark:border-slate-700 dark:bg-slate-800"
      >
        <CalendarDays className="h-4 w-4" />
        {label}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Pick a day to view appointments"
          className="absolute right-0 top-12 z-30 w-[280px] rounded-2xl border border-line bg-card p-3 shadow-xl dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-2 flex items-center justify-between">
            <button type="button" aria-label="Previous month" onClick={() => shift(-1)} className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-ink-2 hover:bg-canvas">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-display text-sm font-bold text-ink">{monthTitle.format(new Date(view.year, view.month, 1))}</span>
            <button type="button" aria-label="Next month" onClick={() => shift(1)} className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-ink-2 hover:bg-canvas">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-7 gap-0.5 text-center">
            {WEEKDAYS.map((w) => (
              <span key={w} className="py-1 text-[10px] font-bold uppercase text-muted">
                {w}
              </span>
            ))}
            {monthCells(view.year, view.month).map((day, i) =>
              day ? (
                <button
                  key={i}
                  type="button"
                  onClick={() => pick(day)}
                  aria-current={localToday(day) === today ? 'date' : undefined}
                  className={cn(
                    'h-8 cursor-pointer rounded-lg text-xs font-semibold transition-colors',
                    localToday(day) === today ? 'bg-grove text-white hover:bg-grove/90' : 'text-ink-2 hover:bg-grove-wash hover:text-grove',
                  )}
                >
                  {day.getDate()}
                </button>
              ) : (
                <span key={i} />
              ),
            )}
          </div>
          <p className="mt-2 border-t border-line pt-2 text-[11px] text-muted">Pick a day to see and book appointments.</p>
        </div>
      )}
    </div>
  );
}
