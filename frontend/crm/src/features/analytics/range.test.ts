import { describe, expect, it } from 'vitest';
import { customRangeError } from './api';

describe('custom analytics range (D-026)', () => {
  it('matches the API rules', () => {
    expect(customRangeError('2026-10-01', '')).not.toBeNull();
    expect(customRangeError('2026-10-31', '2026-10-01')).not.toBeNull();
    expect(customRangeError('2026-10-01', '2026-10-01')).toBeNull();
    expect(customRangeError('2024-11-01', '2026-10-31')).toBeNull();
    expect(customRangeError('2024-11-01', '2026-11-01')).toBeNull();
    expect(customRangeError('2024-11-01', '2026-11-02')).not.toBeNull();
    expect(customRangeError('2024-01-31', '2026-01-31')).toBeNull();
    expect(customRangeError('2024-01-31', '2026-02-01')).not.toBeNull();
  });
});
