import { describe, expect, it } from 'vitest';
import { needsDiscountReason } from './discountReason';

const pct = (percent: number, subtotal = 1000) => needsDiscountReason({ mode: 'percent', percent, amount: 0, subtotal });
const amt = (amount: number, subtotal = 1000) => needsDiscountReason({ mode: 'amount', percent: 0, amount, subtotal });

describe('needsDiscountReason (same rule as the server)', () => {
  it('percent: exactly 20 is fine, anything above needs a reason', () => {
    expect(pct(0)).toBe(false);
    expect(pct(20)).toBe(false);
    expect(pct(20.004)).toBe(false); // sent as 20.00
    expect(pct(20.01)).toBe(true);
    expect(pct(25)).toBe(true);
    expect(pct(100)).toBe(true);
  });

  it('amount: compares with 20% of the subtotal in paise', () => {
    expect(amt(200)).toBe(false);
    expect(amt(200.01)).toBe(true);
    expect(amt(199.99)).toBe(false);
    // 20% of 333.33 is 66.666, so 66.66 is fine and 66.67 is above
    expect(amt(66.66, 333.33)).toBe(false);
    expect(amt(66.67, 333.33)).toBe(true);
    // float trap: 0.1 + 0.2 style subtotals
    expect(amt(0.06, 0.1 + 0.2)).toBe(false);
  });

  it('no subtotal: any discount needs a reason, none does not', () => {
    expect(amt(0, 0)).toBe(false);
    expect(amt(1, 0)).toBe(true);
  });
});
