/**
 * Patient display number (CRM-1, backend PR #46).
 *
 * The API stores a plain per-clinic integer (patients.display_number) and
 * searches it as digits. The CRM shows it as a case ID: a short clinic code,
 * then the number padded to 6 digits, e.g. "SPC-000123".
 *
 * The code is clinics.code (editable in Settings). Where the backend does not
 * send it yet, it is worked out from the clinic name the way it always was:
 * the first letter of up to 3 words, or the first 3 letters of a one-word
 * name; the migration filled the column with exactly that. Search sends the
 * digits.
 */

/** 1 to 6 capital letters or digits (same rule as the API). */
export const CLINIC_CODE_PATTERN = /^[A-Z0-9]{1,6}$/;

/** Trim and capitalise what was typed; returns null when it is not a valid code. */
export function normalizeClinicCode(value: string): string | null {
  const code = value.trim().toUpperCase();
  return CLINIC_CODE_PATTERN.test(code) ? code : null;
}

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
  storedCode?: string | null,
): string {
  const padded = padPatientNumber(displayNumber);
  const code = storedCode?.trim() || clinicCode(clinicName);
  return padded ? `${code}-${padded}` : '';
}

/**
 * A search term typed as a case ID ("SPC-000123", "ASC2-000004", "#123",
 * "spc 123", "asc2 4") becomes the digits the API matches on. Anything else
 * (names, phones, emails) is returned unchanged.
 *
 * Clinic codes are 1 to 6 capital letters or digits (CLINIC_CODE_PATTERN):
 * - a code of letters only keeps the old rule: separator optional up to 4
 *   letters ("spc12"), 5 or 6 letters need one;
 * - a code with a digit in it needs a separator (- # or space) and at least
 *   one letter, so a phone number typed with a space ("98765 43210") is never
 *   read as a case ID;
 * - plain digits without "#" stay as typed (phone search).
 */
const CASE_ID_LETTERS = /^\s*#?\s*([A-Za-z]{1,6})(\s*[-#]\s*|\s+|)(\d{1,19})\s*$/;
const CASE_ID_ALNUM = /^\s*#?\s*([A-Za-z0-9]{1,6})\s*[-#\s]\s*(\d{1,19})\s*$/;
const HASH_NUMBER = /^\s*#\s*(\d{1,19})\s*$/;

export function normalizePatientSearch(term: string): string {
  const hash = HASH_NUMBER.exec(term);
  if (hash) return hash[1];

  const letters = CASE_ID_LETTERS.exec(term);
  if (letters && (letters[1].length <= 4 || letters[2] !== '')) {
    return letters[3];
  }

  const alnum = CASE_ID_ALNUM.exec(term);
  if (alnum && /[A-Za-z]/.test(alnum[1])) return alnum[2];

  return term;
}
