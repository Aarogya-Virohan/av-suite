import { describe, expect, it } from 'vitest';
import { feeCategoryLabel, normalizePrice } from './feeItems';

describe('normalizePrice', () => {
  it('accepts rupees with up to 2 decimals', () => {
    expect(normalizePrice('800')).toBe('800.00');
    expect(normalizePrice(' 799.5 ')).toBe('799.50');
    expect(normalizePrice('0')).toBe('0.00');
  });
  it('rejects bad input', () => {
    for (const bad of ['', '-1', '1.234', 'abc', '1e3', '12345678901']) expect(normalizePrice(bad)).toBeNull();
  });
  it('labels categories', () => {
    expect(feeCategoryLabel('exercise_rx')).toBe('Exercise prescription');
    expect(feeCategoryLabel('unknown')).toBe('unknown');
  });
});
