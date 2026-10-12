// Same rule as _value_with_unit in pdf_service.py: degrees and percent sit
// against the number, every other unit (mm) takes a space.
const TIGHT_UNITS = new Set(["°", "%"])

export function formatValue(value: number | string | null | undefined, unit: string): string {
  if (value === null || value === undefined || value === "") return "–"
  // One decimal always, as on the PDF (founders, 13 October 2026, Q4). The
  // backend already rounds to one place, so this pads and never rounds.
  const v = typeof value === "number" ? value.toFixed(1) : String(value)
  if (!unit) return v
  return TIGHT_UNITS.has(unit) ? `${v}${unit}` : `${v} ${unit}`
}
