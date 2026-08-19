import type { Measurement } from "../../types/posture"
import { getSeverityColor } from "../../lib/getSeverityColor"

interface Props {
  measurement: Measurement
}

export default function MeasurementCard({ measurement }: Props) {
  const colors = getSeverityColor(measurement.severity)

  return (
    <div className="print-card bg-white border rounded-xl p-4 shadow-sm">
      <p className="text-sm text-gray-500">
        {measurement.label}
      </p>

      <h2 className="text-3xl font-bold mt-2">
        {measurement.value === null || measurement.value === undefined
          ? "\u2014"
          : `${measurement.value}${measurement.unit}`}
      </h2>

      <div
        className={`
          inline-block mt-3 px-3 py-1 rounded-full border text-sm font-medium
          ${colors.badgeBg}
          ${colors.badgeText}
          ${colors.badgeBorder}
        `}
      >
        {measurement.severityLabel}
      </div>
    </div>
  )
}