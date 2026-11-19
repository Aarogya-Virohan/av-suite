import { describe, expect, it } from 'vitest';
import { accessState, dateInputToIso, isoToDateInput } from './entitlement';

const NOW = Date.parse('2026-11-19T10:00:00Z');

describe('entitlement helpers', () => {
  it('maps a date to midnight IST and back', () => {
    expect(dateInputToIso('2026-12-01')).toBe('2026-11-30T18:30:00.000Z');
    expect(isoToDateInput('2026-11-30T18:30:00.000Z')).toBe('2026-12-01');
    expect(dateInputToIso('')).toBeNull();
  });

  it('follows the backend validity rule', () => {
    expect(accessState(null, NOW)).toBe('not_granted');
    expect(accessState({ status: 'disabled', valid_from: null, valid_until: null }, NOW)).toBe('disabled');
    expect(accessState({ status: 'enabled', valid_from: '2026-12-01T00:00:00Z', valid_until: null }, NOW)).toBe('scheduled');
    expect(accessState({ status: 'enabled', valid_from: null, valid_until: '2026-11-19T10:00:00Z' }, NOW)).toBe('expired');
    expect(accessState({ status: 'enabled', valid_from: '2026-01-01T00:00:00Z', valid_until: null }, NOW)).toBe('active');
  });
});
