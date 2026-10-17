/**
 * Local date/time helpers for form inputs.
 *
 * `new Date().toISOString()` is UTC. Using it to prefill <input type="date">
 * or <input type="datetime-local"> shows a time 5h30m behind for IST users
 * (and yesterday's date before 5:30 am). Sending a datetime-local value
 * without a time zone made the backend store it as UTC, so a 10:00 am
 * appointment was saved and shown as 3:30 pm. Always use these helpers.
 */

const pad = (n: number) => String(n).padStart(2, '0');

/** Today as YYYY-MM-DD in the user's own time zone. */
export function localToday(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** A Date (or ISO string) as YYYY-MM-DDTHH:mm in local time, for datetime-local inputs. */
export function toLocalDateTimeInput(value: Date | string = new Date()): string {
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return '';
  return `${localToday(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * A datetime-local value (local wall time, no zone) as a UTC ISO string for the API.
 * Returns the input unchanged if it cannot be parsed, so validation can report it.
 */
export function localDateTimeInputToISO(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}
