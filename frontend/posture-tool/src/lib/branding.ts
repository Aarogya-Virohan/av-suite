// Letterhead fallback, 13 October 2026. Same values as AV_FALLBACK in
// backend/app/services/posture/pdf_service.py; change both together.
// Clinic details will come from the marketplace (AV Suite core); until then
// every report carries these. Onkar's placeholders: "AV Clinic" stands in for
// a clinic name.
export const AV_FALLBACK = {
  clinicName: "AV Clinic",
  phone: "+91 88680 00760",
  email: "aarogyavirohan@gmail.com",
}

// Only an inline PNG or JPEG is shown as a clinic logo, the same rule the PDF
// applies (_safe_logo in pdf_service.py). Anything else falls back to the
// clinic's initials.
const LOGO_DATA_URI = /^data:image\/(png|jpeg);base64,[A-Za-z0-9+/]+={0,2}$/

export function safeLogo(value: unknown): string {
  if (typeof value !== "string" || value.length > 3_000_000) return ""
  return LOGO_DATA_URI.test(value) ? value : ""
}

export function initials(name: string): string {
  return name
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
}

export function present(v: unknown): boolean {
  return v !== null && v !== undefined && String(v).trim() !== ""
}
