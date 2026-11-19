'use client';

import React, { useEffect, useRef, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { inputClass } from '@/components/ui/brand';
import { cn } from '@/lib/cn';
import { formatIndianDate, INVALID_DATE, ISO_DAY, parseIndianDate } from '@/lib/dates';

/**
 * Date input that always reads and writes dd/mm/yyyy, whatever the browser
 * locale (a native date input follows the OS, often mm/dd/yyyy). The value is
 * an ISO day (yyyy-mm-dd), '' when empty, or INVALID_DATE for unparseable text.
 * The calendar button opens the browser's own picker.
 */
export function DateField({
  id,
  value,
  onChange,
  onBlur,
  invalid,
  className,
  ariaLabel,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  invalid?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  const [text, setText] = useState(() => formatIndianDate(value));
  const pickerRef = useRef<HTMLInputElement>(null);

  // Follow outside changes (form reset, URL change) unless the user is mid-typing an invalid value.
  useEffect(() => {
    if (value === INVALID_DATE) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setText(formatIndianDate(value));
  }, [value]);

  const commit = (raw: string) => {
    if (!raw.trim()) return onChange('');
    const iso = parseIndianDate(raw);
    onChange(iso ?? INVALID_DATE);
  };

  return (
    <div className={cn('relative', className)}>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        placeholder="dd/mm/yyyy"
        aria-label={ariaLabel}
        aria-invalid={invalid}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          const iso = parseIndianDate(e.target.value);
          if (iso || !e.target.value.trim()) onChange(iso ?? '');
        }}
        onBlur={(e) => {
          commit(e.target.value);
          onBlur?.();
        }}
        className={cn(inputClass, 'pr-10 tabular-nums', invalid && 'border-danger')}
      />
      <button
        type="button"
        aria-label="Open calendar"
        onClick={() => pickerRef.current?.showPicker?.()}
        className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 cursor-pointer place-items-center rounded-md text-slate-400 transition-colors hover:bg-slate-100 hover:text-ink"
      >
        <CalendarDays className="h-4 w-4" />
      </button>
      <input
        ref={pickerRef}
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        value={ISO_DAY.test(value) ? value : ''}
        onChange={(e) => {
          setText(formatIndianDate(e.target.value));
          onChange(e.target.value);
        }}
        className="pointer-events-none absolute bottom-0 right-0 h-0 w-0 opacity-0"
      />
    </div>
  );
}
