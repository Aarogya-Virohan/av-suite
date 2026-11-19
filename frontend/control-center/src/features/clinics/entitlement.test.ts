import { describe, expect, it } from 'vitest';
import { accessState, fromDateToIso, isoToFromDate, isoToUntilDate, untilDateToIso } from './entitlement';

const NOW = Date.parse('2026-11-19T10:00:00Z');

describe('entitlement dates', () => {
  it('maps valid_from to 00:00 IST of that day and back', () => {
    expect(fromDateToIso('2026-12-01')).toBe('2026-11-30T18:30:00.000Z');
    expect(isoToFromDate('2026-11-30T18:30:00.000Z')).toBe('2026-12-01');
    expect(fromDateToIso('')).toBeNull();
  });

  it('makes the end date inclusive: sends next day 00:00 IST, shows the picked day', () => {
    const stored = untilDateToIso('2026-12-10');
    expect(stored).toBe('2026-12-10T18:30:00.000Z'); // = 11 Dec 00:00 IST
    expect(isoToUntilDate(stored)).toBe('2026-12-10');
    expect(untilDateToIso('')).toBeNull();
  });

  it('keeps access through the whole end day, IST', () => {
    const until = untilDateToIso('2026-11-19');
    const lastMinute = Date.parse('2026-11-19T23:59:00+05:30');
    const nextMorning = Date.parse('2026-11-20T00:00:00+05:30');
    expect(accessState({ status: 'enabled', valid_from: null, valid_until: until }, lastMinute)).toBe('active');
    expect(accessState({ status: 'enabled', valid_from: null, valid_until: until }, nextMorning)).toBe('expired');
  });

  it('allows a one-day grant (from = until)', () => {
    const from = fromDateToIso('2026-11-19');
    const until = untilDateToIso('2026-11-19');
    expect(accessState({ status: 'enabled', valid_from: from, valid_until: until }, NOW)).toBe('active');
  });

  it('follows the backend validity rule', () => {
    expect(accessState(null, NOW)).toBe('not_granted');
    expect(accessState({ status: 'disabled', valid_from: null, valid_until: null }, NOW)).toBe('disabled');
    expect(accessState({ status: 'enabled', valid_from: '2026-12-01T00:00:00Z', valid_until: null }, NOW)).toBe('scheduled');
    expect(accessState({ status: 'enabled', valid_from: null, valid_until: '2026-11-19T10:00:00Z' }, NOW)).toBe('expired');
    expect(accessState({ status: 'enabled', valid_from: '2026-01-01T00:00:00Z', valid_until: null }, NOW)).toBe('active');
  });
});
