"use client"

import { useEffect, useState } from "react"

import { listPatientReports, type SavedReportListing } from "@/lib/api"
import { formatReportDate } from "@/lib/formatDate"

// Posture reports already saved for this patient. Opening one shows the saved
// report again (without photographs) and its PDF can be downloaded again.

export default function PreviousReports({
  patientId,
  version,
  onOpen,
  busyId,
}: {
  patientId: string
  /** Bumped after a new report is saved, to load the list again. */
  version: number
  onOpen: (reportId: string) => void
  busyId: string | null
}) {
  const [loaded, setLoaded] = useState<{ key: string; reports: SavedReportListing[] } | null>(null)
  const [failed, setFailed] = useState(false)
  const key = `${patientId}:${version}`

  useEffect(() => {
    let cancelled = false
    listPatientReports(patientId)
      .then((reports) => {
        if (!cancelled) {
          setLoaded({ key, reports })
          setFailed(false)
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [patientId, key])

  const reports = loaded && loaded.key === key ? loaded.reports : null
  if (failed || !reports || reports.length === 0) return null

  return (
    <div className="mt-4 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-5 sm:p-6" data-testid="previous-reports">
      <h2 className="font-display text-[17px] font-bold text-[#141A33]">Earlier posture reports</h2>
      <ul className="mt-3 divide-y divide-[#EFE8D6]">
        {reports.map((r) => (
          <li key={r.reportId} className="flex items-center justify-between gap-3 py-2.5">
            <span className="min-w-0">
              <span className="block font-mono text-[12.5px] font-semibold text-[#141A33]">{r.reportId}</span>
              <span className="block text-[12.5px] text-[#5D6380]">
                {r.assessmentDate ? formatReportDate(r.assessmentDate) : ""}
                {r.clinician ? ` · ${r.clinician}` : ""}
              </span>
            </span>
            <button
              type="button"
              disabled={busyId !== null}
              onClick={() => onOpen(r.reportId)}
              className="h-9 flex-none rounded-lg border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[13px] font-semibold text-[#141A33] transition hover:bg-[#F3EEE2] disabled:opacity-50"
              data-testid="open-report"
            >
              {busyId === r.reportId ? "Opening..." : "Open"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
