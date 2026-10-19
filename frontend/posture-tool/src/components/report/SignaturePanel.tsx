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
 *
 * 19 October 2026, founders asked for a bigger diagram: same layout as the
 * PDF page 3, the chart on its own across the full width, the key under
 * it, and the regions below in two columns.
 */

interface Props {
  data: BiomechanicalSignature
}

export default function SignaturePanel({ data }: Props) {
  return (
    <section className="print-section">
      <SectionTitle title="Biomechanical Signature" />

      {data.svg && (
        <div
          className="mx-auto mt-4 w-full max-w-[640px] [&_svg]:h-auto [&_svg]:w-full"
          dangerouslySetInnerHTML={{ __html: data.svg }}
        />
      )}

      <p className="mx-auto mt-2 max-w-[560px] text-center text-[12px] leading-relaxed text-[#5D6380]">
        Each axis is one measurement. A point sits on the ring of its grade, normal at the centre
        and severe at the edge, so a smaller shape is a better result. A region shows the worst
        grade among its measurements.
      </p>

      {/* Two columns filled top to bottom, head to toe, as on the PDF,
          whatever the number of regions. */}
      <ul className="mt-5 gap-x-10 sm:columns-2">
        {data.regions.map((r) => (
          <li key={r.id} className="flex break-inside-avoid items-center justify-between border-b border-[#E3DCCB] py-2.5">
            <span className="text-[14px] text-[#141A33]">{r.label}</span>
            {r.worst && r.worstLabel ? (
              <SeverityBadge severity={r.worst} label={r.worstLabel} />
            ) : (
              <span className="text-[12px] text-[#5D6380]">
                {r.parameters.length === 0 ? "No parameter" : "Not measured"}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
