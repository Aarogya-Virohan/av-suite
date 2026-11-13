import { describe, expect, it } from 'vitest';
import {
  addDays,
  appointmentDayLabel,
  appointmentListQuery,
  orderForDashboard,
  overlapsExisting,
  pageInfo,
} from './listing';
import type { Appointment } from '../../types/api';

const appt = (id: string, iso: string, extra: Partial<Appointment> = {}) =>
  ({ id, scheduled_at: iso, therapist_id: 't1', status: 'scheduled', duration_minutes: 30, ...extra }) as Appointment;

describe('appointment list query (D-028)', () => {
  it('upcoming starts today, soonest first, paged', () => {
    expect(appointmentListQuery({ view: 'upcoming', today: '2026-11-01', status: 'all', page: 3 })).toEqual({
      start_date: '2026-11-01', status: undefined, order: 'asc', offset: 100, limit: 50,
    });
  });
  it('past ends yesterday, newest first, keeps the status', () => {
    expect(appointmentListQuery({ view: 'past', today: '2026-03-01', status: 'no_show', page: 1 })).toEqual({
      end_date: '2026-02-28', status: 'no_show', order: 'desc', offset: 0, limit: 50,
    });
  });
  it('a day is one India day, not paged', () => {
    expect(appointmentListQuery({ view: 'day', today: '2026-11-01', day: '2026-11-05', status: 'cancelled', page: 4 })).toEqual({
      date: '2026-11-05', status: 'cancelled', order: 'asc', offset: 0, limit: 500,
    });
  });
});

describe('addDays and pageInfo', () => {
  it('crosses months, years and leap days', () => {
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31');
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01');
  });
  it('gives the shown range and page count', () => {
    expect(pageInfo(1, 50, 523, 50)).toEqual({ pages: 11, first: 1, last: 50 });
    expect(pageInfo(11, 50, 523, 23)).toEqual({ pages: 11, first: 501, last: 523 });
    expect(pageInfo(1, 50, 0, 0)).toEqual({ pages: 1, first: 0, last: 0 });
  });
});

describe('dashboard order', () => {
  const now = new Date('2026-11-01T14:40:00Z').getTime(); // 20:10 IST
  it('puts upcoming first, then recent past, with no duplicates', () => {
    const today = [appt('a', '2026-11-01T03:30:00Z'), appt('b', '2026-11-01T15:00:00Z')];
    const next = [appt('c', '2026-11-02T04:30:00Z')];
    const recent = [appt('d', '2026-10-31T10:00:00Z'), appt('a', '2026-11-01T03:30:00Z')];
    expect(orderForDashboard([today, next, recent], now).map((r) => r.id)).toEqual(['b', 'c', 'a', 'd']);
  });
  it('keeps at most 7 rows', () => {
    const many = Array.from({ length: 12 }, (_, i) => appt(`u${i}`, new Date(now + (i + 1) * 3600_000).toISOString()));
    expect(orderForDashboard([many], now)).toHaveLength(7);
  });
});

describe('overlapsExisting', () => {
  const existing = [
    appt('x', '2026-11-01T04:30:00Z'), // 10:00-10:30 IST
    appt('y', '2026-11-01T06:30:00Z', { status: 'cancelled' }), // ignored
    appt('z', '2026-11-01T08:30:00Z', { therapist_id: 't2' }), // other therapist
  ];
  it('catches a long visit that starts before another one (old check missed it)', () => {
    expect(overlapsExisting(existing, 't1', '2026-11-01T03:30:00Z', 90)).toBe(true); // 09:00-10:30
  });
  it('allows back-to-back visits', () => {
    expect(overlapsExisting(existing, 't1', '2026-11-01T05:00:00Z', 30)).toBe(false); // 10:30
    expect(overlapsExisting(existing, 't1', '2026-11-01T04:00:00Z', 30)).toBe(false); // 09:30-10:00
  });
  it('ignores cancelled visits and other therapists', () => {
    expect(overlapsExisting(existing, 't1', '2026-11-01T06:30:00Z', 30)).toBe(false);
    expect(overlapsExisting(existing, 't1', '2026-11-01T08:30:00Z', 30)).toBe(false);
  });
  it('returns false without a therapist or a valid time', () => {
    expect(overlapsExisting(existing, '', '2026-11-01T04:30:00Z', 30)).toBe(false);
    expect(overlapsExisting(existing, 't1', 'not a date', 30)).toBe(false);
  });
});

describe('appointmentDayLabel', () => {
  it('adds the year only for another year', () => {
    const now = new Date('2026-11-01T10:00:00+05:30');
    expect(appointmentDayLabel('2026-11-01T04:30:00Z', now)).toBe('1 Nov');
    expect(appointmentDayLabel('2025-01-25T04:30:00Z', now)).toBe('25 Jan 2025');
  });
});
