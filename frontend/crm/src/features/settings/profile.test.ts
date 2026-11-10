import { describe, expect, it } from 'vitest';
import { EMPTY_PROFILE, clinicProfileErrors } from './profile';

describe('clinic profile checks (D-026)', () => {
  it('accepts empty fields', () => {
    expect(clinicProfileErrors(EMPTY_PROFILE)).toEqual({});
  });
  it('matches the API rules', () => {
    const errors = clinicProfileErrors({ ...EMPTY_PROFILE, pincode: '12345', gstin: '09ABC', email: 'x@y' });
    expect(Object.keys(errors).sort()).toEqual(['email', 'gstin', 'pincode']);
    expect(clinicProfileErrors({ ...EMPTY_PROFILE, pincode: '201301', gstin: '09ABCDE1234F1Z5', email: 'c@x.com' })).toEqual({});
  });
});
