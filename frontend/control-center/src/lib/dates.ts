/*
 * Date entry in dd/mm/yyyy (en-IN) for every date field in the console.
 * Form values stay ISO calendar days (yyyy-mm-dd) so they compare as strings.
 */
export const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/** "05/12/2026" -> "2026-12-05"; null when not a real date. */
export function parseIndianDate(text: string): string | null {
  const m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(text.trim());
  if (!m) return null;
  const [, d, mo, y] = m;
  const day = Number(d);
  const month = Number(mo);
  const year = Number(y);
  if (month < 1 || month > 12 || day < 1 || year < 1900 || year > 2999) return null;
  const check = new Date(Date.UTC(year, month - 1, day));
  if (check.getUTCMonth() !== month - 1 || check.getUTCDate() !== day) return null;
  return `${y}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/** "2026-12-05" -> "05/12/2026"; '' for empty or malformed input. */
export function formatIndianDate(iso: string): string {
  if (!ISO_DAY.test(iso)) return '';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

/** Marker a DateField reports for text that is not a valid date, so forms can show an error. */
export const INVALID_DATE = 'invalid';
