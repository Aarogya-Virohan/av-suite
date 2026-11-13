import type { Lead } from '../../types/api';
import { localToday } from '../../lib/datetime';
import { lostReasonLabel } from './lostReasons';

/*
 * Lead export and month-by-month counts (founder feedback C-11). Built from
 * the list the page already loads (up to 500 leads, Decisions.md L-40);
 * months use the user's local time zone, not UTC.
 */

const csvCell = (v: unknown) => {
  const s = v == null ? '' : String(v);
  // Quote everything that could break a row; neutralise spreadsheet formulas.
  const safe = /^[=+\-@]/.test(s) ? `'${s}` : s;
  return /[",\n\r]/.test(safe) || safe !== s ? `"${safe.replace(/"/g, '""')}"` : safe;
};

export function leadsToCsv(leads: Lead[]): string {
  const header = ['Name', 'Phone', 'Email', 'Source', 'Stage', 'Lost reason', 'Lost remark', 'Created on', 'Notes'];
  const rows = leads.map((l) => [
    l.name,
    l.phone,
    l.email,
    l.source ? l.source.replace(/_/g, ' ') : '',
    l.stage,
    lostReasonLabel(l.lost_reason),
    l.lost_remark,
    l.created_at ? localToday(new Date(l.created_at)) : '',
    l.notes,
  ]);
  // BOM so Excel opens the UTF-8 file with the right characters.
  return '﻿' + [header, ...rows].map((r) => r.map(csvCell).join(',')).join('\r\n');
}

export type MonthRow = { key: string; label: string; total: number; converted: number; lost: number; open: number };

const monthLabel = new Intl.DateTimeFormat('en-IN', { month: 'short', year: 'numeric' });

/** Counts for the last `months` months including the current one, newest first. */
export function monthlyLeadCounts(leads: Lead[], months = 6, now: Date = new Date()): MonthRow[] {
  const rows: MonthRow[] = [];
  for (let i = 0; i < months; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = localToday(d).slice(0, 7);
    rows.push({ key, label: monthLabel.format(d), total: 0, converted: 0, lost: 0, open: 0 });
  }
  const byKey = new Map(rows.map((r) => [r.key, r]));
  for (const l of leads) {
    if (!l.created_at) continue;
    const row = byKey.get(localToday(new Date(l.created_at)).slice(0, 7));
    if (!row) continue;
    row.total += 1;
    if (l.stage === 'converted' || l.converted_patient_id) row.converted += 1;
    else if (l.stage === 'lost') row.lost += 1;
    else row.open += 1;
  }
  return rows;
}

export function downloadCsv(filename: string, csv: string) {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
