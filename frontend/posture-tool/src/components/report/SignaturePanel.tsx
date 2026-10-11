import { BiomechanicalSignature } from "@/types/posture"
import { getSeverityColor } from "@/lib/getSeverityColor"

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
    <section className="print-section rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-3xl font-bold text-slate-900">Biomechanical Signature</h2>
      <p className="mt-2 max-w-2xl text-sm text-slate-500">
        Each axis is one measurement. Inner ring normal, then mild and moderate, outer ring
        severe. A region shows the worst grade among its measurements.
      </p>

      <div className="mt-6 grid grid-cols-1 items-center gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        {data.svg && (
          <div
            className="mx-auto w-full max-w-[460px] [&_svg]:h-auto [&_svg]:w-full"
            dangerouslySetInnerHTML={{ __html: data.svg }}
          />
        )}

        <ul className="divide-y divide-slate-100">
          {data.regions.map((r) => {
            const colors = r.worst ? getSeverityColor(r.worst) : null
            return (
              <li key={r.id} className="flex items-center justify-between py-3">
                <span className="text-slate-800">{r.label}</span>
                {colors && r.worstLabel ? (
                  <span
                    className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${colors.badgeBg} ${colors.badgeText} ${colors.badgeBorder}`}
                  >
                    {r.worstLabel}
                  </span>
                ) : (
                  <span className="text-xs text-slate-400">
                    {r.parameters.length === 0 ? "No parameter" : "Not measured"}
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
