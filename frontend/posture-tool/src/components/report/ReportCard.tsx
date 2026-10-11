import ReportHeader from "./ReportHeader"
import ViewSection from "./ViewSection"
import SynthesisPanel from "./SynthesisPanel"
import SignaturePanel from "./SignaturePanel"

import { PostureReport } from "@/types/posture"

interface Props {
  data: PostureReport
}

// Footer wording as given by Onkar, 11 October 2026, identical to the PDF
// footer in pdf_service.py. Change both together.
function PoweredBy() {
  return (
    <div className="border-t border-[#D9E3E4] pt-4 text-center">
      {/* Each segment is kept whole, so a phone breaks the line between
          segments ("AV Suite" never splits across two lines). */}
      <p className="flex flex-wrap items-baseline justify-center gap-x-1.5 gap-y-0.5 text-[11px] uppercase leading-relaxed tracking-[0.08em]">
        <span className="whitespace-nowrap">
          <span className="font-bold text-[#3B6A70]">&copy; Powered by </span>
          <span className="font-bold text-[#2F3336]">Aarogya Virohan</span>
        </span>
        <span className="text-[#4E888F]">&bull;</span>
        <span className="whitespace-nowrap text-[13px] font-bold text-[#3B6A70]">AV Suite</span>
        <span className="text-[#4E888F]">&bull;</span>
        <span className="whitespace-nowrap text-[10px] text-[#6B7378]">(A Clinical Exercise Prescription Tool)</span>
      </p>
    </div>
  )
}

export default function ReportCard({
  data
}: Props) {
  const anyUpload = [data.views.side, data.views.front, data.views.back].some(
    (v) => v?.captureSource === "upload"
  )

  return (
    <div className="relative overflow-hidden rounded-xl border border-[#D9E3E4] bg-white px-4 py-6 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] sm:px-10 sm:py-10">

      {/* Logo mark as a watermark, same as the PDF. Purely decorative,
          behind everything and ignored by pointer and screen reader. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/brand/av_mark.png"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-[40%] w-[55%] max-w-[380px] -translate-x-1/2 select-none opacity-[0.025]"
      />

      <div className="relative space-y-10">

        <ReportHeader patient={data.patient} reportId={data.reportId} />

        <ViewSection
          viewName="Sagittal (Side) Plane"
          data={data.views.side}
          view="side"
        />

        <ViewSection
          viewName="Coronal (Front) Plane"
          data={data.views.front}
          view="front"
        />

        <ViewSection
          viewName="Posterior (Back) Plane"
          data={data.views.back}
          view="back"
        />

        {data.signature && <SignaturePanel data={data.signature} />}

        <SynthesisPanel data={data.synthesis} />

        <div className="rounded-md border border-[#D9E3E4] px-4 py-3.5">
          <p className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#3B6A70]">Disclaimer</p>
          {/* Founders' wording, verbatim, 10 October 2026. Same text as
              DISCLAIMER in pdf_service.py; do not reword without them. */}
          <p className="mt-1.5 text-[13px] leading-relaxed text-[#2F3336]">
            This structural screening report is generated via automated 2D optical tracking. It highlights static biomechanical asymmetries to predict localized tissue loading. It is not a standalone clinical diagnosis and must be correlated with patient symptoms and functional movement by a licensed physiotherapist.
          </p>
          <p className="mt-2 text-[12px] text-[#6B7378]">Left and right refer to the patient&apos;s own sides.</p>
          {anyUpload && (
            <p className="mt-1 text-[12px] text-[#6B7378]">
              {/* Same text as UPLOAD_NOTE in pdf_service.py. */}
              Views marked &ldquo;Uploaded photo&rdquo; were measured the same way as a guided capture, but were not taken with the guided camera&rsquo;s level check. Compare them with later visits with that in mind.
            </p>
          )}
          {data.analysisVersion && (
            <p className="mt-1 text-[11px] text-[#8A9296]">
              Analysis version {data.analysisVersion}. Values and grades are only comparable with reports carrying the same version.
            </p>
          )}
        </div>

        <PoweredBy />

      </div>
    </div>
  )
}
