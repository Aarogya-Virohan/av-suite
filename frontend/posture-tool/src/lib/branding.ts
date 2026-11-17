// Aarogya Virohan's own contact, on the letterhead only when the report has
// no clinic (13 October 2026). The "AV Clinic" placeholder name was removed
// on 17 November 2026: the report names the signed-in clinic, or no clinic.
export const AV_FALLBACK = {
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
