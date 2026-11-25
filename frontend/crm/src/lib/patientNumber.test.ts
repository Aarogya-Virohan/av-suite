import { describe, expect, it } from 'vitest';
import {
  clinicCode,
  formatPatientNumber,
  normalizeClinicCode,
  normalizePatientSearch,
  padPatientNumber,
} from './patientNumber';

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
  it('uses the stored clinic code when there is one, the name rule when not', () => {
    expect(formatPatientNumber(123, 'SpineAct Physio Clinic', 'ADP')).toBe('ADP-000123');
    expect(formatPatientNumber(123, 'SpineAct Physio Clinic', null)).toBe('SPC-000123');
    expect(formatPatientNumber(123, 'SpineAct Physio Clinic', '  ')).toBe('SPC-000123');
    expect(formatPatientNumber(123, 'SpineAct Physio Clinic', undefined)).toBe('SPC-000123');
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
  it('finds a patient by a code that has digits in it (ASC2-000004)', () => {
    expect(normalizePatientSearch('ASC2-000004')).toBe('000004');
    expect(normalizePatientSearch('asc2-000004')).toBe('000004');
    expect(normalizePatientSearch('asc2 4')).toBe('4');
    expect(normalizePatientSearch('ASC2#4')).toBe('4');
    expect(normalizePatientSearch('#ASC2-4')).toBe('4');
    expect(normalizePatientSearch('A1B2C3-12')).toBe('12');
  });
  it('takes 5 and 6 letter codes only with a separator', () => {
    expect(normalizePatientSearch('ABCDEF-12')).toBe('12');
    expect(normalizePatientSearch('abcde 12')).toBe('12');
    expect(normalizePatientSearch('ABCDEF12')).toBe('ABCDEF12');
  });
  it('rejects a 7 character code', () => {
    expect(normalizePatientSearch('ABCDEFG-12')).toBe('ABCDEFG-12');
    expect(normalizePatientSearch('ASC2345-4')).toBe('ASC2345-4');
  });
  it('reads a code with a digit only when a separator marks where the number starts', () => {
    // No separator: "ASC24" is the old letters rule (ASC + 24), as "spc12" always was.
    expect(normalizePatientSearch('ASC24')).toBe('24');
    // A digit code with no separator and no letters-only prefix stays as typed.
    expect(normalizePatientSearch('A1B24')).toBe('A1B24');
    expect(normalizePatientSearch('2ASC4')).toBe('2ASC4');
  });
  it('keeps phone numbers whole, also with spaces or a country code', () => {
    expect(normalizePatientSearch('9876543210')).toBe('9876543210');
    expect(normalizePatientSearch('98765 43210')).toBe('98765 43210');
    expect(normalizePatientSearch('+91 9876543210')).toBe('+91 9876543210');
    expect(normalizePatientSearch('91-9876543210')).toBe('91-9876543210');
  });
  it('leaves names, phones and emails alone', () => {
    expect(normalizePatientSearch('Ravi')).toBe('Ravi');
    expect(normalizePatientSearch('9876543210')).toBe('9876543210');
    expect(normalizePatientSearch('ravi@x.in')).toBe('ravi@x.in');
    expect(normalizePatientSearch('ravi2@x.in')).toBe('ravi2@x.in');
    expect(normalizePatientSearch('Ravi Kumar')).toBe('Ravi Kumar');
  });
});

describe('normalizeClinicCode', () => {
  it('capitalises and trims a valid code', () => {
    expect(normalizeClinicCode(' adp1 ')).toBe('ADP1');
    expect(normalizeClinicCode('A')).toBe('A');
    expect(normalizeClinicCode('ABCDEF')).toBe('ABCDEF');
  });
  it('rejects empty, long or non letter/digit codes', () => {
    for (const bad of ['', '   ', 'ABCDEFG', 'AB-1', 'AB 1', 'A_B', 'ए']) {
      expect(normalizeClinicCode(bad)).toBeNull();
    }
  });
});
