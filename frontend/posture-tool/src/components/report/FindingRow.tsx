import type { Measurement } from "@/types/posture"

interface FindingRowProps {
  finding: Measurement
}

export default function FindingRow({ finding }: FindingRowProps) {
  return (
    <div className="flex justify-between p-2 border">
      <span>{finding.label}</span>
      <span>
        {finding.value}
        {finding.unit}
      </span>
      <span>{finding.severityLabel}</span>
    </div>
  )
}
