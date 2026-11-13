import { describe, expect, it } from 'vitest';
import { LOST_REASONS, lostReasonError, lostReasonLabel } from './lostReasons';

describe('lost reasons (D-026)', () => {
  it('uses the six reasons from the API', () => {
    expect(LOST_REASONS.map((r) => r.value)).toEqual(['denied', 'better_price', 'asked_for_discount', 'offer', 'call_not_picked', 'other']);
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
