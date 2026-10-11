// Same branding as the PDF (pdf_service.py, 11 October 2026): Aarogya
// Virohan logo left, document title right, patient details in one tinted
// band. Once the tool is joined to the marketplace the clinic's own logo and
// details replace the logo here, and Aarogya Virohan stays only in the
// footer (decisions.md, 11 October).

import { formatReportDate } from "@/lib/formatDate"

interface ReportHeaderProps {
  patient: {
    name: string
    age: number
    gender?: string
    caseRef: string
    assessmentDate: string
    clinician: string
  }
  reportId?: string
}

function present(v: unknown): boolean {
  return v !== null && v !== undefined && String(v).trim() !== ""
}

export default function ReportHeader({ patient, reportId }: ReportHeaderProps) {
  const ageSex = [patient.age, patient.gender].filter(present).join(" / ")
  const date = formatReportDate(patient.assessmentDate)

  // A field left empty at intake is left out, as on the PDF: an empty
  // "Clinician" on a clinical document reads as an omission.
  const details: [string, string][] = (
    [
      ["Patient", patient.name],
      ["Age / Sex", ageSex],
      ["Case ref.", patient.caseRef],
      ["Clinician", patient.clinician],
      ["Assessed", date],
      ["Report ID", reportId ?? ""],
    ] as [string, string][]
  ).filter(([, v]) => present(v))

  return (
    <div>
      <div className="flex flex-col gap-3 border-b-[1.5px] border-[#4E888F] pb-4 sm:flex-row sm:items-end sm:justify-between">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/av_logo_wordmark.png" alt="Aarogya Virohan" className="h-8 w-auto self-start sm:h-10" />
        <div className="sm:text-right">
          <p className="text-[17px] font-bold tracking-tight text-[#2F3336]">Posture Assessment Report</p>
          {/* Name and date, as under the PDF title. */}
          <p className="mt-0.5 text-[11px] uppercase tracking-[0.14em] text-[#3B6A70]">
            {[patient.name, date].filter(present).join("  ·  ") || "Clinical Posture Assessment"}
          </p>
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 rounded-md border border-[#D9E3E4] bg-[#F3F7F7] px-5 py-4 sm:grid-cols-3">
        {details.map(([label, value]) => (
          // The report ID is one unbroken code; on a phone it gets the full
          // row rather than wrapping in the middle.
          <div key={label} className={label === "Report ID" ? "col-span-2 min-w-0 sm:col-span-1" : "min-w-0"}>
            <dt className="text-[10.5px] uppercase tracking-[0.08em] text-[#6B7378]">{label}</dt>
            <dd className={`mt-0.5 text-[14.5px] font-bold text-[#2F3336] ${label === "Report ID" ? "whitespace-nowrap" : "break-words"}`}>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
