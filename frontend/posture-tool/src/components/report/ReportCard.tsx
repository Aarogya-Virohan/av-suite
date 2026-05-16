import type { PostureReport } from "@/types/posture"
import ReportHeader from "./ReportHeader"
import ViewSection from "./ViewSection"

interface ReportCardProps {
  data: PostureReport
}

export default function ReportCard({ data }: ReportCardProps) {
  return (
    <article className="space-y-6">
      <ReportHeader patient={data.patient} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
          Global Posture Index
        </p>

        <div className="mt-2 flex flex-wrap items-end gap-3">
          <h2 className="text-5xl font-bold text-slate-900">
            {data.globalIndex.score}
          </h2>

          <p className="pb-2 text-lg text-slate-600">
            {data.globalIndex.descriptor}
          </p>
        </div>
      </section>

      <ViewSection viewName="Side View" data={data.views.side} />
      <ViewSection viewName="Front View" data={data.views.front} />
      <ViewSection viewName="Back View" data={data.views.back} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900">
          Corrective Synthesis
        </h2>

        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
          <div>
            <h3 className="font-semibold text-slate-900">Hypertonic</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
              {data.synthesis.hypertonic.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-slate-900">Inhibited</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
              {data.synthesis.inhibited.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-slate-900">Protocol</h3>
            <ul className="mt-3 space-y-3 text-slate-700">
              {data.synthesis.correctiveProtocol.map((item) => (
                <li key={item.exercise}>
                  <span className="font-medium text-slate-900">
                    {item.exercise}
                  </span>
                  <span className="block text-sm text-slate-600">
                    {item.dosage}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </article>
  )
}
