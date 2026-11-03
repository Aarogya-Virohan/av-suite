import { describe, expect, it } from 'vitest';
import { intervalWords, REPEAT_OPTIONS, scheduleStatus } from './schedule';
import type { Schedule } from './types';

const base: Schedule = {
  id: 's1',
  patient_id: 'p1',
  instrument_id: 'phq9',
  short_name: 'PHQ-9',
  interval_days: 28,
  state: 'due',
  next_due_at: '2026-10-01T06:00:00Z',
  last_completed_at: null,
  created_at: '2026-09-01T06:00:00Z',
  created_by_name: 'Arjun Mehta',
};

describe('schedule words', () => {
  it('reads the interval', () => {
    expect(intervalWords(7)).toBe('every week');
    expect(intervalWords(28)).toBe('every 4 weeks');
    expect(intervalWords(10)).toBe('every 10 days');
  });

  it('describes each state', () => {
    expect(scheduleStatus(base)).toMatch(/^Due since \d/);
    expect(scheduleStatus({ ...base, state: 'upcoming' })).toMatch(/^Next due \d/);
    expect(scheduleStatus({ ...base, state: 'waiting', next_due_at: null })).toBe('Link sent, waiting for the patient');
    expect(scheduleStatus({ ...base, state: 'consent_withdrawn', next_due_at: null })).toBe(
      'Paused: the patient withdrew consent',
    );
  });

  it('offers only intervals the API accepts (1 to 52 weeks)', () => {
    for (const o of REPEAT_OPTIONS) {
      if (o.weeks !== null) expect(o.weeks >= 1 && o.weeks <= 52).toBe(true);
    }
    expect(REPEAT_OPTIONS[0].weeks).toBeNull();
  });
});
