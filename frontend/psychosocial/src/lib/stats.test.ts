import { describe, expect, it } from 'vitest';
import { barWidth, lastDays, referralLine, statsQuery } from './stats';

describe('stats helpers', () => {
  it('builds an inclusive range of days', () => {
    expect(lastDays(90, new Date(2026, 9, 22))).toEqual({ from: '2026-07-25', to: '2026-10-22' });
    expect(lastDays(1, new Date(2026, 0, 1))).toEqual({ from: '2026-01-01', to: '2026-01-01' });
  });

  it('adds the screener only when one is chosen', () => {
    expect(statsQuery('2026-10-01', '2026-10-31', '')).toBe('from=2026-10-01&to=2026-10-31');
    expect(statsQuery('2026-10-01', '2026-10-31', 'gad7')).toBe('from=2026-10-01&to=2026-10-31&instrument=gad7');
  });

  it('never prints a hidden referral figure', () => {
    expect(referralLine({ count: 7, rate_percent: 53.8, suppressed: false }, 13)).toBe('7 of 13 (53.8%)');
    expect(referralLine({ count: null, rate_percent: null, suppressed: true }, 13)).toBe('Hidden to protect a small group');
    // The flag wins even if numbers came along with it.
    expect(referralLine({ count: 3, rate_percent: 23.1, suppressed: true }, 13)).toBe('Hidden to protect a small group');
  });

  it('sizes bars against the total and draws none for hidden counts', () => {
    expect(barWidth(6, 13)).toBe(46.2);
    expect(barWidth(null, 13)).toBe(0);
    expect(barWidth(0, 0)).toBe(0);
  });
});
