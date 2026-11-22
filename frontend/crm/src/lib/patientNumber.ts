/**
 * Patient display number (CRM-1, backend PR #46).
 *
 * The API stores a plain per-clinic integer (patients.display_number) and
 * searches it as digits. The CRM shows it as a case ID: a short clinic code,
 * then the number padded to 6 digits, e.g. "SPC-000123".
 *
 * There is no clinic code column yet, so the code is taken from the clinic
 * name: the first letter of up to 3 words, or the first 3 letters of a
 * one-word name. It is only for display; search sends the digits.
 */

const WORD = /[A-Za-z][A-Za-z0-9]*/g;

export function clinicCode(clinicName: string | null | undefined): string {
  const words = (clinicName ?? '').match(WORD) ?? [];
  if (words.length === 0) return 'PT';
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return words
    .slice(0, 3)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

export function padPatientNumber(displayNumber: number | null | undefined): string {
  if (displayNumber == null || !Number.isFinite(displayNumber) || displayNumber < 0) return '';
  return String(Math.trunc(displayNumber)).padStart(6, '0');
}

export function formatPatientNumber(
  displayNumber: number | null | undefined,
  clinicName: string | null | undefined,
): string {
  const padded = padPatientNumber(displayNumber);
  return padded ? `${clinicCode(clinicName)}-${padded}` : '';
}

/**
 * A search term typed as a case ID ("SPC-000123", "#123", "spc 123") becomes
 * the digits the API matches on. Anything else (names, phones, emails) is
 * returned unchanged.
 */
const CASE_ID = /^\s*#?\s*([A-Za-z]{1,4})?\s*[-#\s]?\s*(\d{1,19})\s*$/;

export function normalizePatientSearch(term: string): string {
  const match = CASE_ID.exec(term);
  if (!match) return term;
  // Plain digits stay as typed: they may be a phone number or part of one.
  if (!match[1] && !term.includes('#')) return term;
  return match[2];
}
