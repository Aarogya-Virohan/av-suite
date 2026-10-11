// Same rule as _value_with_unit in pdf_service.py: degrees and percent sit
// against the number, every other unit (mm) takes a space.
const TIGHT_UNITS = new Set(["°", "%"])

export function formatValue(value: number | string | null | undefined, unit: string): string {
  if (value === null || value === undefined || value === "") return "–"
  // Two decimals always, as on the PDF: 11.9 beside 2.36 in one column
  // looked like a different precision. Pads only, never changes a value.
  const v = typeof value === "number" ? value.toFixed(2) : String(value)
  if (!unit) return v
  return TIGHT_UNITS.has(unit) ? `${v}${unit}` : `${v} ${unit}`
}
