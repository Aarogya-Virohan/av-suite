// Letterhead and patient box, 13 October 2026, the same as the PDF
// (_letterhead and _patient_box in pdf_service.py). With clinic details
// (report.branding, to come from the marketplace) the band is the clinic's
// letterhead: logo and name, the head doctor, contact. Without them it is
// Aarogya Virohan's, with the assessing physiotherapist on the right.
// Empty fields are left out, never shown as blank labels.

import type { PostureReport } from "@/types/posture"
import { formatReportDate } from "@/lib/formatDate"
import { AV_FALLBACK, initials, present, safeLogo } from "@/lib/branding"

type Props = Pick<PostureReport, "patient" | "reportId" | "branding">

function Divider() {
  return <span aria-hidden="true" className="hidden w-px self-stretch bg-white/20 sm:block" />
}

export function Letterhead({ patient, branding }: Props) {
  const hasClinic = present(branding?.clinicName)

  if (hasClinic && branding) {
    const name = String(branding.clinicName).trim()
    const logo = safeLogo(branding.logo)
    const contact = [branding.phone, branding.email, branding.website].filter(present)
    return (
      <div className="flex flex-col gap-4 bg-[linear-gradient(115deg,#0B1238_0%,#121F4A_55%,#1B4A54_100%)] px-5 py-5 text-white sm:flex-row sm:items-center sm:gap-6 sm:px-10">
        <div className="flex min-w-0 items-center gap-3.5 sm:flex-[1.25]">
          <div className="flex h-12 w-12 flex-none items-center justify-center rounded-xl bg-white">
            {logo ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={logo} alt="" className="max-h-10 max-w-10" />
            ) : (
              <span className="font-display text-[17px] font-extrabold text-[#1C7A54]">{initials(name)}</span>
            )}
          </div>
          <div className="min-w-0">
            <p className="font-display text-[17px] font-extrabold leading-tight">{name}</p>
            {present(branding.addressLine) && (
              <p className="mt-0.5 text-[12px] text-[#C9D0EA]">{branding.addressLine}</p>
            )}
          </div>
        </div>
        {present(branding.doctorName) && (
          <>
            <Divider />
            <div className="sm:flex-[0.85]">
              <p className="font-display text-[14px] font-bold">{branding.doctorName}</p>
              {present(branding.doctorDegree) && (
                <p className="text-[12px] font-semibold text-[#C1FF72]">{branding.doctorDegree}</p>
              )}
              {present(branding.doctorRegNo) && (
                <p className="text-[12px] text-[#C9D0EA]">Reg. No. {branding.doctorRegNo}</p>
              )}
            </div>
          </>
        )}
        {contact.length > 0 && (
          <>
            <Divider />
            <div className="text-[12px] leading-relaxed text-[#C9D0EA] sm:flex-[0.75]">
              {contact.map((c, i) => (
                <p key={c} className={i === 0 && c === branding.phone ? "font-semibold text-white" : ""}>
                  {c}
                </p>
              ))}
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 bg-[linear-gradient(115deg,#0B1238_0%,#121F4A_55%,#1B4A54_100%)] px-5 py-5 text-white sm:flex-row sm:items-center sm:gap-6 sm:px-10">
      <div className="sm:flex-[1.25]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/av_logo_wordmark_white.png" alt="Aarogya Virohan" className="h-8 w-auto" />
        <p className="mt-2 text-[12px] text-[#C9D0EA]">
          {AV_FALLBACK.phone} &nbsp;·&nbsp; {AV_FALLBACK.email}
        </p>
      </div>
      {present(patient.clinician) && (
        <>
          <Divider />
          <div className="sm:flex-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#C9D0EA]">
              Assessing physiotherapist
            </p>
            <p className="mt-1 font-display text-[15px] font-bold">{patient.clinician}</p>
          </div>
        </>
      )}
    </div>
  )
}

export function PatientBox({ patient, reportId, branding }: Props) {
  const hasClinic = present(branding?.clinicName)
  const ageSex = [present(patient.age) ? `${patient.age} Y` : "", patient.gender ?? ""]
    .filter(present)
    .join(" / ")
  const height =
    typeof patient.heightCm === "number" && Number.isFinite(patient.heightCm)
      ? `${patient.heightCm} cm`
      : ""

  const left: [string, string][] = [
    ["Patient name", patient.name],
    ["Age / Sex", ageSex],
    ["Height", height],
    ["Case ref.", patient.caseRef],
  ]
  // With a clinic letterhead the head doctor is in the band and the assessing
  // physiotherapist is here; in the fallback the assessor is in the band, so
  // this row names the clinic instead. Same as the PDF.
  const right: [string, string][] = [
    ["Report ID", reportId ?? ""],
    ["Assessed on", formatReportDate(patient.assessmentDate)],
    hasClinic ? ["Assessed by", patient.clinician] : ["Clinic", AV_FALLBACK.clinicName],
  ]

  const column = (rows: [string, string][]) => (
    // minmax(0, 1fr): a plain 1fr column grows to fit its longest word, so on
    // a phone the report ID pushed past the box (27 October 2026).
    <dl className="grid min-w-0 flex-1 content-start grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 sm:grid-cols-[7.5rem_minmax(0,1fr)]">
      {rows
        .filter(([, v]) => present(v))
        .map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="self-center text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#5D6380]">{label}</dt>
            <dd
              className={
                label === "Patient name"
                  ? "font-display text-[16px] font-bold text-[#141A33] break-words"
                  : `min-w-0 text-[14px] font-semibold text-[#141A33] ${label === "Report ID" ? "break-all text-[13px] tabular-nums sm:whitespace-nowrap sm:text-[14px]" : "break-words"}`
              }
            >
              {value}
            </dd>
          </div>
        ))}
    </dl>
  )

  return (
    <div>
      <div className="flex flex-col gap-3 rounded-2xl border-[1.5px] border-[#D9D1BF] bg-[#FFFDF7] px-5 py-4 sm:flex-row sm:gap-6">
        {column(left)}
        <span aria-hidden="true" className="hidden w-px bg-[#E3DCCB] sm:block" />
        {column(right)}
      </div>
      <h1 className="mt-6 text-center font-display text-[18px] font-extrabold tracking-[0.16em] text-[#0B1238] sm:text-[20px]">
        POSTURE ASSESSMENT REPORT
      </h1>
    </div>
  )
}
