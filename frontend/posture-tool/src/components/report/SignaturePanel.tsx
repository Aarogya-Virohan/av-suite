import { BiomechanicalSignature } from "@/types/posture"
import SectionTitle from "./SectionTitle"
import SeverityBadge from "./SeverityBadge"

/*
 * Biomechanical Signature, founders' Q5, 10 October 2026: a regional
 * profile in place of the single score. It adds no number of its own. Each
 * region shows the worst grade among its measurements, and the chart puts
 * every measurement on the ring of its grade.
 *
 * The SVG is drawn by the server from the same data the PDF redraws from,
 * so the two match. It is rendered as markup because it comes from our own
 * renderer, never from user input; labels are escaped there.
 */

interface Props {
  data: BiomechanicalSignature
}

export default function SignaturePanel({ data }: Props) {
  return (
    <section className="print-section">
      <SectionTitle title="Biomechanical Signature" />

      <div className="mt-4 grid grid-cols-1 items-center gap-6 md:grid-cols-2 md:gap-8">
        {data.svg && (
          <div
            className="mx-auto w-full max-w-[420px] [&_svg]:h-auto [&_svg]:w-full"
            dangerouslySetInnerHTML={{ __html: data.svg }}
          />
        )}

        <div>
          <ul>
            {data.regions.map((r) => (
              <li key={r.id} className="flex items-center justify-between border-b border-[#EDF2F2] py-2.5">
                <span className="text-[14px] text-[#2F3336]">{r.label}</span>
                {r.worst && r.worstLabel ? (
                  <SeverityBadge severity={r.worst} label={r.worstLabel} />
                ) : (
                  <span className="text-[12px] text-[#6B7378]">
                    {r.parameters.length === 0 ? "No parameter" : "Not measured"}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[12px] leading-relaxed text-[#8A9296]">
            Each axis is one measurement. Inner ring normal, then mild and moderate, outer ring
            severe. A region shows the worst grade among its measurements.
          </p>
        </div>
      </div>
    </section>
  )
}
