import data from "@/src/data/mockAnalysis.json"
import type { PostureAnalysis } from "@/src/types/posture"
import FindingRow from "../report/FindingRow"

export default function AnalysisPanel() {
  const analysis = data as PostureAnalysis

  return (
    <div>
      <h2 className="text-2xl">Score: {analysis.overallScore}</h2>

      {analysis.findings.map((f, i) => (
        <FindingRow key={i} finding={f} />
      ))}
    </div>
  )
}
