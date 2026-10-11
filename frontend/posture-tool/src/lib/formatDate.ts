// "2026-10-11" -> "11 Oct 2026", same as _display_date in pdf_service.py.
// ISO dates read as a database value on a clinical document, and 11/10
// against 10/11 is ambiguous. Anything that is not an ISO date is returned
// as it came.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

export function formatReportDate(value: string | null | undefined): string {
  if (!value) return ""
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!m) return value
  const month = Number(m[2])
  if (month < 1 || month > 12) return value
  return `${Number(m[3])} ${MONTHS[month - 1]} ${m[1]}`
}
