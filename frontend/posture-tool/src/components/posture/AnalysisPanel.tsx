import data from "@/data/mockAnalysis.json"
import type { PostureReport } from "@/types/posture"
import MeasurementCard from "../report/MeasurementCard"

export default function AnalysisPanel() {
  const analysis = data as PostureReport
  const measurements = Object.values(analysis.views).flatMap(
    (view) => view.measurements
  )

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
          Global Posture Index
        </p>

        <div className="mt-2 flex flex-wrap items-end gap-3">
          <h2 className="text-5xl font-bold text-slate-900">
            {analysis.globalIndex.score}
          </h2>

          <p className="pb-2 text-lg text-slate-600">
            {analysis.globalIndex.descriptor}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {measurements.map((measurement) => (
          <MeasurementCard
            key={`${measurement.label}-${measurement.value}`}
            measurement={measurement}
          />
        ))}
      </div>
    </div>
  )
}
