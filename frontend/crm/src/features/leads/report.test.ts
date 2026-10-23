import { describe, expect, it } from 'vitest';
import type { Lead } from '../../types/api';
import { leadsToCsv, monthlyLeadCounts } from './report';

const lead = (over: Partial<Lead>): Lead =>
  ({ id: '1', clinic_id: 'c', name: 'A', phone: '9', email: null, source: null, stage: 'new', notes: null, assigned_to: null, converted_patient_id: null, created_at: '2026-10-10T10:00:00Z', updated_at: '2026-10-10T10:00:00Z', ...over }) as Lead;

describe('leads report (C-11)', () => {
  it('escapes commas, quotes, newlines and formula starts', () => {
    const csv = leadsToCsv([lead({ name: 'Rao, K', notes: 'said "call"\nlater', email: '=cmd' })]);
    const line = csv.replace('﻿', '').split('\r\n')[1];
    expect(line).toBe('"Rao, K",9,"\'=cmd",,new,2026-10-10,"said ""call""\nlater"');
  });

  it('counts by local month with converted / lost / open', () => {
    const now = new Date(2026, 9, 24);
    const rows = monthlyLeadCounts(
      [
        lead({ stage: 'converted' }),
        lead({ stage: 'lost' }),
        lead({ stage: 'contacted' }),
        lead({ stage: 'new', created_at: '2026-09-02T10:00:00Z' }),
        lead({ created_at: '2025-01-01T10:00:00Z' }),
      ],
      3,
      now,
    );
    expect(rows.map((r) => [r.key, r.total, r.converted, r.lost, r.open])).toEqual([
      ['2026-10', 3, 1, 1, 1],
      ['2026-09', 1, 0, 0, 1],
      ['2026-08', 0, 0, 0, 0],
    ]);
  });
});
