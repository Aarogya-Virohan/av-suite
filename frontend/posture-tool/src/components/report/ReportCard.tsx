import { Letterhead, PatientBox } from "./ReportHeader"
import ViewSection from "./ViewSection"
import SynthesisPanel from "./SynthesisPanel"
import SignaturePanel from "./SignaturePanel"

import { PostureReport } from "@/types/posture"

interface Props {
  data: PostureReport
}

// Footer, 13 October 2026, the same as the PDF: the Aarogya Virohan mark,
// then "POWERED BY AAROGYA VIROHAN . AV SUITE". The bracketed tagline was
// removed on Onkar's word. Change both together.
function PoweredBy() {
  return (
    <div className="border-t border-[#E3DCCB] pt-4 text-center">
      <p className="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5 text-[11px] uppercase tracking-[0.1em]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/av_mark.png" alt="" aria-hidden="true" className="mr-0.5 h-4 w-auto" />
        <span className="whitespace-nowrap">
          <span className="font-bold text-[#5D6380]">Powered by </span>
          <span className="font-bold text-[#0B1238]">Aarogya Virohan</span>
        </span>
        <span className="text-[#1C7A54]">&bull;</span>
        <span className="whitespace-nowrap font-bold text-[#1C7A54]">AV Suite</span>
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
    <div className="relative overflow-hidden rounded-2xl border border-[#E3DCCB] bg-[#F8F4EA] shadow-[0_1px_2px_rgba(11,18,56,0.05),0_12px_32px_-16px_rgba(11,18,56,0.22)]">

      <Letterhead patient={data.patient} reportId={data.reportId} branding={data.branding} />

      <div className="relative px-4 py-6 sm:px-10 sm:py-8">

        {/* Logo mark as a watermark, same as the PDF. Purely decorative,
            behind everything and ignored by pointer and screen reader. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/av_mark.png"
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-[38%] w-[55%] max-w-[380px] -translate-x-1/2 select-none opacity-[0.03]"
        />

        <div className="relative space-y-10">

          <PatientBox patient={data.patient} reportId={data.reportId} branding={data.branding} />

          <ViewSection
            viewName="Sagittal (Side) Plane"
            data={data.views.side}
          />

          <ViewSection
            viewName="Coronal (Front) Plane"
            data={data.views.front}
          />

          <ViewSection
            viewName="Posterior (Back) Plane"
            data={data.views.back}
          />

          {data.signature && <SignaturePanel data={data.signature} />}

          <SynthesisPanel data={data.synthesis} />

          <div className="rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-4 py-3.5">
            <p className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#1C7A54]">Disclaimer</p>
            {/* Founders' wording, verbatim, 10 October 2026. Same text as
                DISCLAIMER in pdf_service.py; do not reword without them. */}
            <p className="mt-1.5 text-[13px] leading-relaxed text-[#141A33]">
              This structural screening report is generated via automated 2D optical tracking. It highlights static biomechanical asymmetries to predict localized tissue loading. It is not a standalone clinical diagnosis and must be correlated with patient symptoms and functional movement by a licensed physiotherapist.
            </p>
            <p className="mt-2 text-[12px] text-[#5D6380]">Left and right refer to the patient&apos;s own sides.</p>
            {anyUpload && (
              <p className="mt-1 text-[12px] text-[#5D6380]">
                {/* Same text as UPLOAD_NOTE in pdf_service.py. */}
                Views marked &ldquo;Uploaded photo&rdquo; were measured the same way as a guided capture, but were not taken with the guided camera&rsquo;s level check. Compare them with later visits with that in mind.
              </p>
            )}
            {data.analysisVersion && (
              <p className="mt-1 text-[11px] text-[#5D6380]">
                Analysis version {data.analysisVersion}. Values and grades are only comparable with reports carrying the same version.
              </p>
            )}
          </div>

          <PoweredBy />

        </div>
      </div>
    </div>
  )
}
