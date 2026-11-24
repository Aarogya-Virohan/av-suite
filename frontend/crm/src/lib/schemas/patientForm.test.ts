import { describe, expect, it } from 'vitest';
import { patientFormSchema, toPatientPayload, MAX_PATIENT_AGE } from './index';

const base = {
  first_name: 'Rajesh',
  last_name: 'Kumar',
  date_of_birth: '',
  age: '',
  phone: '9876543210',
  gender: null,
  chief_complaint: 'Lower back pain',
  referral_source: null,
  status: 'active' as const,
};

function messages(values: Record<string, unknown>) {
  const result = patientFormSchema.safeParse(values);
  return result.success ? [] : result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`);
}

describe('patient form: age or date of birth is required', () => {
  it('rejects a patient with neither age nor date of birth', () => {
    expect(messages(base)).toEqual(['age: Enter the age or the date of birth']);
    expect(messages({ ...base, age: '   ', date_of_birth: null })).toEqual(['age: Enter the age or the date of birth']);
  });

  it('accepts an age alone, a date of birth alone, or both', () => {
    expect(messages({ ...base, age: '42' })).toEqual([]);
    expect(messages({ ...base, date_of_birth: '1984-02-01' })).toEqual([]);
    expect(messages({ ...base, age: '42', date_of_birth: '1984-02-01' })).toEqual([]);
    expect(messages({ ...base, age: '0' })).toEqual([]);
  });

  it('rejects ages that are not whole numbers from 0 to 130', () => {
    for (const bad of ['-1', '4.5', 'abc', String(MAX_PATIENT_AGE + 1), '1e2']) {
      expect(messages({ ...base, age: bad })).toEqual([`age: Age must be a whole number from 0 to ${MAX_PATIENT_AGE}`]);
    }
    expect(messages({ ...base, age: String(MAX_PATIENT_AGE) })).toEqual([]);
  });

  it('keeps the other required fields required', () => {
    expect(messages({ ...base, age: '30', first_name: '' })).toEqual(['first_name: First name is required']);
  });
});

describe('toPatientPayload', () => {
  it('sends age as a number and blanks as null', () => {
    const payload = toPatientPayload({ ...base, age: ' 42 ' });
    expect(payload.age).toBe(42);
    expect(payload.date_of_birth).toBeNull();
  });

  it('sends a null age when only the date of birth is filled', () => {
    const payload = toPatientPayload({ ...base, date_of_birth: '1984-02-01' });
    expect(payload.age).toBeNull();
    expect(payload.date_of_birth).toBe('1984-02-01');
  });
});
