import { describe, expect, it } from 'vitest';
import { clinicCode, formatPatientNumber, normalizePatientSearch, padPatientNumber } from './patientNumber';

describe('clinicCode', () => {
  it('uses initials of up to three words', () => {
    expect(clinicCode('SpineAct Physio Clinic')).toBe('SPC');
    expect(clinicCode('Dr. Mehta Physiotherapy & Rehab Centre')).toBe('DMP');
  });
  it('uses three letters of a one-word name', () => {
    expect(clinicCode('SpineAct')).toBe('SPI');
  });
  it('falls back when the name has no letters', () => {
    expect(clinicCode('')).toBe('PT');
    expect(clinicCode(null)).toBe('PT');
    expect(clinicCode('123')).toBe('PT');
  });
});

describe('formatPatientNumber', () => {
  it('pads to six digits', () => {
    expect(padPatientNumber(7)).toBe('000007');
    expect(formatPatientNumber(123, 'SpineAct Physio Clinic')).toBe('SPC-000123');
  });
  it('keeps numbers longer than six digits whole', () => {
    expect(padPatientNumber(1234567)).toBe('1234567');
  });
  it('returns empty text for a missing number', () => {
    expect(formatPatientNumber(undefined, 'X')).toBe('');
  });
});

describe('normalizePatientSearch', () => {
  it('turns a case ID into digits', () => {
    expect(normalizePatientSearch('SPC-000123')).toBe('000123');
    expect(normalizePatientSearch('spc 12')).toBe('12');
    expect(normalizePatientSearch('#45')).toBe('45');
  });
  it('leaves names, phones and emails alone', () => {
    expect(normalizePatientSearch('Ravi')).toBe('Ravi');
    expect(normalizePatientSearch('9876543210')).toBe('9876543210');
    expect(normalizePatientSearch('ravi@x.in')).toBe('ravi@x.in');
    expect(normalizePatientSearch('Ravi Kumar')).toBe('Ravi Kumar');
  });
});
