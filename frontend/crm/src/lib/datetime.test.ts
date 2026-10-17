import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { localDateTimeInputToISO, localToday, toLocalDateTimeInput } from './datetime';

// Clinics run in IST; the original bug only shows with a non-UTC zone.
const originalTZ = process.env.TZ;
beforeAll(() => {
  process.env.TZ = 'Asia/Kolkata';
});
afterAll(() => {
  process.env.TZ = originalTZ;
});

describe('datetime helpers (IST)', () => {
  it('converts a 10:00 local appointment to 04:30 UTC, not 10:00 UTC', () => {
    expect(localDateTimeInputToISO('2026-10-13T10:00')).toBe('2026-10-13T04:30:00.000Z');
  });

  it('round-trips an API timestamp into the same local wall time', () => {
    expect(toLocalDateTimeInput('2026-10-13T04:30:00.000Z')).toBe('2026-10-13T10:00');
  });

  it('gives the local date before 5:30 am IST (UTC is still the previous day)', () => {
    const earlyMorningIST = new Date('2026-10-11T22:20:00.000Z'); // 03:50 IST on 12 Oct
    expect(localToday(earlyMorningIST)).toBe('2026-10-12');
    expect(earlyMorningIST.toISOString().slice(0, 10)).toBe('2026-10-11');
  });

  it('leaves unparseable input unchanged for validation to report', () => {
    expect(localDateTimeInputToISO('not a date')).toBe('not a date');
    expect(toLocalDateTimeInput('not a date')).toBe('');
  });
});
