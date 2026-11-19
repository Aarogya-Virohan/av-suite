import { describe, expect, it } from 'vitest';
import { formatIndianDate, parseIndianDate } from './dates';

describe('dd/mm/yyyy dates', () => {
  it('parses Indian order', () => {
    expect(parseIndianDate('05/12/2026')).toBe('2026-12-05');
    expect(parseIndianDate('5/1/2027')).toBe('2027-01-05');
    expect(parseIndianDate('31-12-2026')).toBe('2026-12-31');
  });
  it('rejects impossible dates and US order', () => {
    expect(parseIndianDate('31/02/2026')).toBeNull();
    expect(parseIndianDate('12/31/2026')).toBeNull();
    expect(parseIndianDate('2026-12-05')).toBeNull();
    expect(parseIndianDate('')).toBeNull();
  });
  it('formats back', () => {
    expect(formatIndianDate('2026-12-05')).toBe('05/12/2026');
    expect(formatIndianDate('')).toBe('');
  });
});
