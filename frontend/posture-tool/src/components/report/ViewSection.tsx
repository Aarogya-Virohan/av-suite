import type { ViewData } from "../../types/posture"
import { formatValue } from "@/lib/formatValue"
import SectionTitle from "./SectionTitle"
import SeverityBadge from "./SeverityBadge"

interface Props {
  viewName: string
  data: ViewData
  view?: "side" | "front" | "back"
}

// A direction is only meaningful once the magnitude is a finding. Below that
// it is decided by landmark noise, and showing it would put a direction on
// every healthy patient. Matches the PDF, which hides it at the same grades.
const SIDE_HIDDEN_SEVERITIES: ReadonlySet<string> = new Set([
  "none",
  "insufficient_data",
  "not_available"
])

// Same layout as the PDF (pdf_service._view_section, 11 October 2026): the
// annotated photograph at its own proportions beside a table of the view's
// measurements, the capture source as a flag beside the title.
const CAPTION: Record<string, string> = {
  side: "Viewed from the side",
  front: "Viewed from the front",
  back: "Viewed from behind",
}

export default function ViewSection({ viewName, data, view }: Props) {
  const caption = view ? CAPTION[view] : undefined
  // Since 11 October 2026 the capture source is a plain detail under the
  // table, as on the PDF, not an amber flag: the report reaches the patient,
  // and the explanation is given once in the disclaimer box.
  const sourceText =
    data.captureSource === "upload"
      ? "Uploaded photo"
      : data.captureSource === "camera"
        ? "Guided camera capture"
        : null

  return (
    <section className="print-section">
      <SectionTitle
        title={viewName}
        aside={
          caption ? (
            <span className="text-[11px] uppercase tracking-[0.1em] text-[#6B7378]">{caption}</span>
          ) : undefined
        }
      />

      {/* Photo column sized by the photo itself, so a narrow portrait image
          does not leave a gap before the table. A real table, so the value
          and finding columns line up across rows and a long badge cannot
          spill past the edge. */}
      <div className="mt-4 flex flex-col gap-5 md:flex-row md:items-start md:gap-7">
        <div className="flex shrink-0 justify-center">
          {data.photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={data.photoUrl}
              alt={`${viewName}, annotated`}
              className="h-auto max-h-[560px] w-auto max-w-full rounded-md border border-[#D9E3E4]"
            />
          ) : (
            <div className="flex h-56 w-44 items-center justify-center rounded-md border border-dashed border-slate-300 text-center text-sm text-slate-400">
              Annotated image unavailable
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          {/* Phone: one row per parameter, name on its own line and the
              value and grade under it. Three columns at phone width
              squeezed the names to one word a line and pushed the longest
              badge past the card's edge. */}
          {data.measurements.length > 0 && (
            <ul className="sm:hidden">
              {data.measurements.map((m) => {
                const showSide =
                  m.sideLabel !== null &&
                  m.sideLabel !== undefined &&
                  !SIDE_HIDDEN_SEVERITIES.has(m.severity)
                return (
                  <li key={m.paramId} className="border-b border-[#EDF2F2] py-3 first:border-t first:border-t-[#D9E3E4]">
                    <p className="text-[15px] leading-snug text-[#2F3336]">{m.label}</p>
                    {showSide && <p className="mt-0.5 text-[12.5px] text-[#6B7378]">{m.sideLabel}</p>}
                    <div className="mt-1.5 flex items-center justify-between gap-3">
                      <span className="text-[17px] font-bold tabular-nums text-[#2F3336]">
                        {formatValue(m.value, m.unit)}
                      </span>
                      <SeverityBadge severity={m.severity} label={m.severityLabel} />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}

          {data.measurements.length === 0 ? (
            <p className="py-3 text-sm italic text-slate-400">No measurements available for this view.</p>
          ) : (
            <table className="hidden w-full border-collapse sm:table">
              <thead>
                <tr className="border-b border-[#D9E3E4] text-[10.5px] uppercase tracking-[0.08em] text-[#6B7378]">
                  <th className="pb-1.5 text-left font-bold">Parameter</th>
                  <th className="px-3 pb-1.5 text-right font-bold sm:px-4">Value</th>
                  <th className="pb-1.5 text-left font-bold">Finding</th>
                </tr>
              </thead>
              <tbody>
                {data.measurements.map((m) => {
                  const showSide =
                    m.sideLabel !== null &&
                    m.sideLabel !== undefined &&
                    !SIDE_HIDDEN_SEVERITIES.has(m.severity)
                  return (
                    <tr key={m.paramId} className="border-b border-[#EDF2F2] align-middle">
                      <td className="py-2.5 pr-2 text-[14px] leading-snug text-[#2F3336]">
                        {m.label}
                        {showSide && <span className="mt-0.5 block text-[12px] text-[#6B7378]">{m.sideLabel}</span>}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-right text-[15px] font-bold tabular-nums text-[#2F3336] sm:px-4">
                        {formatValue(m.value, m.unit)}
                      </td>
                      <td className="w-px whitespace-nowrap py-2.5">
                        <SeverityBadge severity={m.severity} label={m.severityLabel} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {data.interpretation && (
            <p className="mt-4 rounded-md bg-[#F3F7F7] px-3.5 py-2.5 text-[13.5px] leading-relaxed text-[#2F3336]">
              <span className="mr-2 text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#3B6A70]">Summary</span>
              {data.interpretation}
            </p>
          )}

          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[12.5px]">
            {sourceText && (
              <>
                <dt className="text-[#6B7378]">Photograph</dt>
                <dd className="text-[#2F3336]">{sourceText}</dd>
              </>
            )}
            <dt className="text-[#6B7378]">Landmark visibility</dt>
            <dd className="text-[#2F3336]">{(data.accuracy * 100).toFixed(1)}%</dd>
          </dl>
        </div>
      </div>
    </section>
  )
}
