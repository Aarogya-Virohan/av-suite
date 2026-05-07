import type { Finding } from "@/src/types/posture"

interface FindingRowProps {
  finding: Finding
}

export default function FindingRow({ finding }: FindingRowProps) {
  return (
    <div className="flex justify-between p-2 border">
      <span>{finding.bodyPart}</span>
      <span>{finding.observation}</span>
      <span>{finding.severity}</span>
    </div>
  )
}
