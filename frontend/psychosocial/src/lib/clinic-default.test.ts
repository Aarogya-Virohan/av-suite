import { describe, expect, it } from 'vitest';
import { clinicDefaultRepeat, REPEAT_OPTIONS, repeatOptionsWith } from './schedule';
import type { InstrumentSummary } from './types';

const inst = (id: 'phq9' | 'gad7' | 'dass21', short: string, weeks: number | null): InstrumentSummary => ({
  id,
  version: '1',
  short_name: short,
  name: short,
  item_count: 9,
  citation: '',
  default_repeat_weeks: weeks,
});

describe('clinicDefaultRepeat', () => {
  const list = [inst('phq9', 'PHQ-9', 4), inst('gad7', 'GAD-7', 4), inst('dass21', 'DASS-21', null)];

  it('prefills nothing when nothing is ticked or no default is set', () => {
    expect(clinicDefaultRepeat([], list)).toEqual({ weeks: null, mixed: false, hint: null });
    expect(clinicDefaultRepeat(['dass21'], list)).toEqual({ weeks: null, mixed: false, hint: null });
  });

  it('prefills a default the ticked screeners share', () => {
    expect(clinicDefaultRepeat(['phq9'], list)).toEqual({
      weeks: 4,
      mixed: false,
      hint: 'Clinic default for PHQ-9: every 4 weeks.',
    });
    expect(clinicDefaultRepeat(['phq9', 'gad7'], list).weeks).toBe(4);
  });

  it('prefills nothing and says why when the defaults differ', () => {
    const r = clinicDefaultRepeat(['phq9', 'dass21'], list);
    expect(r.weeks).toBeNull();
    expect(r.mixed).toBe(true);
    expect(r.hint).toBe('Clinic defaults differ (PHQ-9 every 4 weeks, DASS-21 just once). Choose one for this link.');
  });

  it('never prefills over a repeat the patient already has', () => {
    const r = clinicDefaultRepeat(['phq9'], list, { phq9: 14 });
    expect(r.weeks).toBeNull();
    expect(r.hint).toBe('Already repeating for this patient: PHQ-9 every 2 weeks. Just once keeps that repeat as it is.');
    const both = clinicDefaultRepeat(['phq9', 'gad7'], list, { phq9: 14, gad7: 28 });
    expect(both.weeks).toBeNull();
    expect(both.hint).toContain('PHQ-9 every 2 weeks, GAD-7 every 4 weeks. Just once keeps those repeats as they are.');
    // A repeat on a screener that is not ticked does not matter.
    expect(clinicDefaultRepeat(['gad7'], list, { phq9: 14 }).weeks).toBe(4);
  });
});

describe('repeatOptionsWith', () => {
  it('keeps the standard list for standard values', () => {
    expect(repeatOptionsWith(4)).toBe(REPEAT_OPTIONS);
    expect(repeatOptionsWith(null)).toBe(REPEAT_OPTIONS);
  });

  it('adds a non-standard stored value in order', () => {
    expect(repeatOptionsWith(3).map((o) => o.weeks)).toEqual([null, 2, 3, 4, 6, 8, 12]);
    expect(repeatOptionsWith(1).find((o) => o.weeks === 1)?.label).toBe('Every week');
  });
});
