import { describe, expect, it } from 'vitest';
import { LOST_REASONS, lostReasonError, lostReasonLabel } from './lostReasons';

describe('lost reasons (D-026)', () => {
  it('uses the six reasons from the API', () => {
    expect(LOST_REASONS.map((r) => r.value)).toEqual([
      'denied', 'better_price', 'asked_for_discount', 'offer', 'call_not_picked',
      'too_far', 'timing_mismatch', 'needs_home_visit', 'cannot_afford', 'went_to_competitor',
      'other',
    ]);
    expect(lostReasonLabel('call_not_picked')).toBe('Call not picked');
  });
  it('needs a reason, and a remark only for Other', () => {
    expect(lostReasonError('', '')).toBe('Choose a reason');
    expect(lostReasonError('offer', '')).toBeNull();
    expect(lostReasonError('other', '  ')).not.toBeNull();
    expect(lostReasonError('other', 'Moved city')).toBeNull();
    expect(lostReasonError('offer', 'x'.repeat(501))).not.toBeNull();
  });
});

describe('lost reasons match the server', () => {
  it('lists every value of the API enum exactly once', async () => {
    // Every reason the server accepts must be selectable, and nothing else.
    const server: string[] = [
      'denied', 'better_price', 'asked_for_discount', 'offer', 'call_not_picked', 'other',
      'too_far', 'timing_mismatch', 'needs_home_visit', 'cannot_afford', 'went_to_competitor',
    ];
    const values = LOST_REASONS.map((r) => r.value);
    expect(new Set(values).size).toBe(values.length);
    expect([...values].sort()).toEqual([...server].sort());
    expect(lostReasonLabel('too_far')).toBe('Location / commute too far');
  });
});
