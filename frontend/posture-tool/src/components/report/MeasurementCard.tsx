import type { Measurement } from "../../types/posture"
import { getSeverityColor } from "../../lib/getSeverityColor"

interface Props {
  measurement: Measurement
}

// A direction is only meaningful once the magnitude is a finding. Below that
// it is decided by landmark noise, and showing it would put a direction on
// every healthy patient. Matches the PDF, which hides it at the same grades.
const SIDE_HIDDEN_SEVERITIES: ReadonlySet<string> = new Set([
  "none",
  "insufficient_data",
  "not_available"
])

export default function MeasurementCard({ measurement }: Props) {
  const colors = getSeverityColor(measurement.severity)

  const showSide =
    measurement.sideLabel !== null &&
    measurement.sideLabel !== undefined &&
    !SIDE_HIDDEN_SEVERITIES.has(measurement.severity)

  return (
    <div className="print-card bg-white border rounded-xl p-4 shadow-sm">
      <p className="text-sm text-gray-500">
        {measurement.label}
      </p>

      {showSide && (
        <p className="text-xs text-gray-400 mt-0.5">
          {measurement.sideLabel}
        </p>
      )}

      <h2 className="text-3xl font-bold mt-2">
        {measurement.value === null || measurement.value === undefined
          ? "\u2013"
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