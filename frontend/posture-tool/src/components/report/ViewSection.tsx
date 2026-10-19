import type { ViewData } from "../../types/posture"
import { formatValue } from "@/lib/formatValue"
import SectionTitle from "./SectionTitle"
import SeverityBadge from "./SeverityBadge"

interface Props {
  viewName: string
  data: ViewData
}

// A direction is only meaningful once the magnitude is a finding. Below that
// it is decided by landmark noise, and showing it would put a direction on
// every healthy patient. Matches the PDF, which hides it at the same grades.
const SIDE_HIDDEN_SEVERITIES: ReadonlySet<string> = new Set([
  "none",
  "insufficient_data",
  "not_available"
])

// Same layout as the PDF (pdf_service._view_section): the annotated
// photograph at its own proportions beside a table of the view's
// measurements. Since 13 October 2026, as on the PDF, no "Viewed from"
// caption (the title says it) and no landmark visibility (a model score
// that reads to a patient as how accurate the test was).
export default function ViewSection({ viewName, data }: Props) {
  // The capture source stays: it decides whether two visits can be
  // compared (founders, 10 October 2026).
  const sourceText =
    data.captureSource === "upload"
      ? "Uploaded photo"
      : data.captureSource === "camera"
        ? "Guided camera capture"
        : null

  return (
    <section className="print-section">
      <SectionTitle title={viewName} />

      {/* Photo column sized by the photo itself, so a narrow portrait image
          does not leave a gap before the table. A real table, so the value
          and finding columns line up across rows and a long badge cannot
          spill past the edge. */}
      <div className="mt-4 flex flex-col gap-5 md:flex-row md:items-start md:gap-7">
        {/* 19 October 2026, founders asked for bigger photographs: up to
            720 px tall (was 560), and at most about half the row on wider
            screens so the table keeps room for its three columns. */}
        <div className="flex shrink-0 justify-center md:max-w-[52%]">
          {data.photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={data.photoUrl}
              alt={`${viewName}, annotated`}
              className="h-auto max-h-[720px] w-auto max-w-full rounded-xl"
            />
          ) : (
            <div className="flex h-56 w-44 items-center justify-center rounded-xl border border-dashed border-[#C9C0AA] text-center text-sm text-[#5D6380]">
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
                  <li key={m.paramId} className="rounded-lg px-3 py-3 even:bg-[#F3EEE2]">
                    <p className="text-[15px] leading-snug text-[#141A33]">{m.label}</p>
                    {showSide && <p className="mt-0.5 text-[12.5px] text-[#5D6380]">{m.sideLabel}</p>}
                    <div className="mt-1.5 flex items-center justify-between gap-3">
                      <span className="font-display text-[17px] font-bold tabular-nums text-[#0B1238]">
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
            <p className="py-3 text-sm italic text-[#5D6380]">No measurements available for this view.</p>
          ) : (
            <table className="hidden w-full border-collapse sm:table">
              <thead>
                <tr className="text-[10.5px] uppercase tracking-[0.1em] text-[#5D6380]">
                  <th className="px-3 pb-2 text-left font-bold">Parameter</th>
                  <th className="px-3 pb-2 text-right font-bold sm:px-4">Value</th>
                  <th className="px-3 pb-2 text-left font-bold">Finding</th>
                </tr>
              </thead>
              <tbody>
                {data.measurements.map((m) => {
                  const showSide =
                    m.sideLabel !== null &&
                    m.sideLabel !== undefined &&
                    !SIDE_HIDDEN_SEVERITIES.has(m.severity)
                  return (
                    <tr key={m.paramId} className="align-middle even:bg-[#F3EEE2]">
                      <td className="rounded-l-lg px-3 py-3 text-[14px] leading-snug text-[#141A33]">
                        {m.label}
                        {showSide && <span className="mt-0.5 block text-[12px] text-[#5D6380]">{m.sideLabel}</span>}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-right font-display text-[15px] font-bold tabular-nums text-[#0B1238] sm:px-4">
                        {formatValue(m.value, m.unit)}
                      </td>
                      <td className="w-px whitespace-nowrap rounded-r-lg px-3 py-3">
                        <SeverityBadge severity={m.severity} label={m.severityLabel} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {data.interpretation && (
            <div className="mt-4 rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-3.5 py-2.5">
              <p className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#1C7A54]">Summary</p>
              <p className="mt-0.5 text-[13.5px] leading-relaxed text-[#141A33]">{data.interpretation}</p>
            </div>
          )}

          {sourceText && (
            <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 text-[12.5px]">
              <dt className="text-[#5D6380]">Photograph</dt>
              <dd className="text-[#141A33]">{sourceText}</dd>
            </dl>
          )}
        </div>
      </div>
    </section>
  )
}
