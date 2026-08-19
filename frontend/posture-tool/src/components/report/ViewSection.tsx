import { ViewData } from "../../types/posture"
import MeasurementCard from "./MeasurementCard"
import AnnotatedImage from "./AnnotatedImage"

interface Props {
  viewName: string
  data: ViewData
}

export default function ViewSection({
  viewName,
  data
}: Props) {
  return (
    <section className="print-section print-page-break print-tight bg-slate-50 rounded-2xl p-6 mt-6">

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">
          {viewName}
        </h2>

        <span className="text-sm text-gray-500">
          Accuracy: {(data.accuracy * 100).toFixed(1)}%
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">

        {data.photoUrl ? (
          <div className="print-image">
            <AnnotatedImage
              src={data.photoUrl}
              alt={viewName}
            />
          </div>
        ) : (
          <div className="flex h-full min-h-[240px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white text-sm text-slate-400">
            No annotated image available
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.measurements.map((measurement, index) => (
            <MeasurementCard
              key={index}
              measurement={measurement}
            />
          ))}
        </div>
      </div>

      <p className="mt-6 text-gray-700">
        {data.interpretation}
      </p>
    </section>
  )
}
