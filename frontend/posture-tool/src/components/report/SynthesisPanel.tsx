import { SynthesisData } from "@/types/posture"

interface Props {
  data: SynthesisData
}

export default function SynthesisPanel({
  data
}: Props) {
  return (
    <section className="print-section print-page-break print-tight rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

      <h2 className="text-3xl font-bold text-slate-900">
        Clinical Master Synthesis
      </h2>

      {/* No exercises since 11 October 2026: the founders removed them from
          the automated report (answer 1b). The physiotherapist prescribes. */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Hypertonic */}
        <div className="rounded-2xl bg-red-50 p-6">
          <h3 className="text-xl font-semibold text-red-700">
            Hypertonic
          </h3>

          <ul className="mt-4 space-y-2 text-slate-700">
            {data.hypertonic.map((muscle) => (
              <li key={muscle}>
                • {muscle}
              </li>
            ))}
          </ul>
        </div>

        {/* Inhibited */}
        <div className="rounded-2xl bg-blue-50 p-6">
          <h3 className="text-xl font-semibold text-blue-700">
            Inhibited
          </h3>

          <ul className="mt-4 space-y-2 text-slate-700">
            {data.inhibited.map((muscle) => (
              <li key={muscle}>
                • {muscle}
              </li>
            ))}
          </ul>
        </div>

      </div>
    </section>
  )
}