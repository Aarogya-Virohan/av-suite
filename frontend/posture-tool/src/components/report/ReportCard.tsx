import ReportHeader from "./ReportHeader"
import ViewSection from "./ViewSection"
import SynthesisPanel from "./SynthesisPanel"

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

      {/* Founders' wording, verbatim, 10 October 2026. Same text as
          DISCLAIMER in pdf_service.py; do not reword without them. */}
      <p className="text-sm font-semibold text-slate-600 border-t pt-4">
        This structural screening report is generated via automated 2D optical tracking. It highlights static biomechanical asymmetries to predict localized tissue loading. It is not a standalone clinical diagnosis and must be correlated with patient symptoms and functional movement by a licensed physiotherapist.
      </p>

    </div>
  )
}