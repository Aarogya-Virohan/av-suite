import ReportHeader from "./ReportHeader"
import ViewSection from "./ViewSection"
import SynthesisPanel from "./SynthesisPanel"
import GlobalIndex from "./GlobalIndex"

import { PostureReport } from "@/types/posture"

interface Props {
  data: PostureReport
}

export default function ReportCard({
  data
}: Props) {
  return (
    <div className="space-y-8">

      <ReportHeader patient={data.patient} />

      <ViewSection
        viewName="Side Plane"
        data={data.views.side}
      />

      <ViewSection
        viewName="Front Plane"
        data={data.views.front}
      />

      <ViewSection
        viewName="Back Plane"
        data={data.views.back}
      />

      <SynthesisPanel data={data.synthesis} />

      <GlobalIndex
        score={data.globalIndex.score}
        descriptor={data.globalIndex.descriptor}
      />

    </div>
  )
}