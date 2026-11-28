// POS-3, 21 November 2026: share the report on WhatsApp the agreed way,
// wa.me with a prefilled text plus the PDF downloaded on the device for
// staff to attach. No public report link (L-4, DPDP consent, still open).
// Phone handling matches the CRM and Psychosocial apps: digits only, India
// code added when missing.

import { formatReportDate } from "./formatDate"
import type { PostureReport } from "@/types/posture"

export function normalisePhone(phone: string | null | undefined): string | null {
  const digits = (phone ?? "").replace(/\D/g, "")
  if (digits.length < 10) return null
  return digits.startsWith("91") && digits.length > 10 ? digits : `91${digits.slice(-10)}`
}

// No grades or findings in the chat bubble (same rule as the Psychosocial
// report message): only who, which clinic, which date, the Patient ID (the
// clinic's CRM ID, POS-10) and that a PDF follows.
export function reportMessage(report: PostureReport): string {
  const first = (report.patient?.name ?? "").trim().split(/\s+/)[0] ?? ""
  const clinic = report.branding?.clinicName?.trim()
  const date = formatReportDate(report.patient?.assessmentDate)
  const patientId = report.patient?.caseRef?.trim()
  return [
    first ? `Hi ${first},` : "Hi,",
    `Your posture assessment report${clinic ? ` from ${clinic}` : ""}${date ? ` dated ${date}` : ""} is attached as a PDF.`,
    ...(patientId ? [`Patient ID: ${patientId}`] : []),
    "Please go through it and bring any questions to your next session.",
  ].join("\n\n")
}

// With no number, wa.me opens WhatsApp's own contact picker.
export function whatsappUrl(phone: string | null, text: string): string {
  return `https://wa.me/${phone ?? ""}?text=${encodeURIComponent(text)}`
}
