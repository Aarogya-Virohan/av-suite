"use client"

import { useState } from "react"

import UploadZone from "@/components/posture/UploadZone"

import ReportCard from "@/components/report/ReportCard"

import LandmarkReview from "@/components/review/LandmarkReview"

import { detectLandmarks, downloadPostureReportPdf, generateReport } from "@/lib/api"

import type { DetectionResult, LandmarkReviewSubmission, PostureReport } from "@/types/posture"

// "review" is the founders' landmark check (Q6, 10 October 2026): no report
// exists until the clinician has confirmed the points.
type Step = "upload" | "review" | "report"

// App bar, brand direction B (13 October 2026): the Midnight band of the AV
// Suite CRM with the white logo and the three steps of an assessment. On
// the report step the report's own letterhead carries the logo, so the bar
// shows only the product name; two logos one above the other read as a
// mistake.
const STEP_ORDER: { key: Step; label: string }[] = [
  { key: "upload", label: "Patient & photos" },
  { key: "review", label: "Landmark check" },
  { key: "report", label: "Report" },
]

function Header({ step }: { step: Step }) {
  const current = STEP_ORDER.findIndex((s) => s.key === step)
  return (
    <header className="bg-[linear-gradient(115deg,#0B1238_0%,#121F4A_60%,#1B4A54_100%)] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3.5">
        {step !== "report" ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src="/brand/av_logo_wordmark_white.png" alt="Aarogya Virohan" className="h-6 w-auto" />
        ) : (
          <span className="font-display text-[15px] font-bold">Aarogya Virohan</span>
        )}
        <span className="rounded-full bg-[#C1FF72] px-2.5 py-0.5 text-[11.5px] font-bold text-[#0B1238]">
          Posture Tool
        </span>
        <ol className="flex w-full items-center gap-1.5 sm:ml-auto sm:w-auto" aria-label="Assessment steps">
          {STEP_ORDER.map((s, i) => {
            const active = i === current
            const done = i < current
            return (
              <li key={s.key} className="flex flex-1 items-center gap-1.5 sm:flex-none">
                <span
                  aria-current={active ? "step" : undefined}
                  className={`flex items-center gap-1.5 whitespace-nowrap text-[12px] font-semibold ${
                    active ? "text-[#C1FF72]" : done ? "text-white" : "text-[#A9B3D6]"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 flex-none items-center justify-center rounded-full text-[11px] font-bold ${
                      active
                        ? "bg-[#C1FF72] text-[#0B1238]"
                        : done
                          ? "bg-white/90 text-[#0B1238]"
                          : "border border-[#4A5585] text-[#A9B3D6]"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className={active ? "" : "hidden sm:inline"}>{s.label}</span>
                </span>
                {i < STEP_ORDER.length - 1 && <span aria-hidden="true" className="h-px flex-1 bg-white/20 sm:w-5 sm:flex-none" />}
              </li>
            )
          })}
        </ol>
      </div>
    </header>
  )
}

const INPUT_CLASS =
  "h-11 w-full rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[15px] text-[#141A33] outline-none transition placeholder:text-[#8B90A8] focus:border-[#4E888F]"

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string | null
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-[12px] text-[#B4231B]">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-[12px] text-[#5D6380]">{hint}</span>
      ) : null}
    </label>
  )
}

export default function Page() {
const [step, setStep] =
useState<Step>("upload")

const [frontImage, setFrontImage] =
useState<string | null>(null)

const [sideImage, setSideImage] =
useState<string | null>(null)

const [backImage, setBackImage] =
useState<string | null>(null)

const [frontFile, setFrontFile] =
useState<File | null>(null)

const [sideFile, setSideFile] =
useState<File | null>(null)

const [backFile, setBackFile] =
useState<File | null>(null)

// Whether each photograph came from the in-app capture screen or from an
// existing file. An uploaded photo skips the tripod, framing and encoding
// protocol, so a measurement taken from one is not comparable with a
// guided capture of the same patient. The report records which it was.
type CaptureSource = "camera" | "upload" | "unknown"

const [frontSource, setFrontSource] =
useState<CaptureSource>("unknown")

const [sideSource, setSideSource] =
useState<CaptureSource>("unknown")

const [backSource, setBackSource] =
useState<CaptureSource>("unknown")

const [patientName, setPatientName] =
useState("")

const [age, setAge] =
useState("")

const [gender, setGender] =
useState("")

const [caseRef, setCaseRef] =
useState("")

const [patientHeightCm, setPatientHeightCm] =
useState("")

const [clinicianName, setClinicianName] =
useState("")

const [report, setReport] =
useState<PostureReport | null>(null)

const [detection, setDetection] =
useState<DetectionResult | null>(null)

const [loading, setLoading] =
useState(false)

// Shown on the intake screen instead of a browser alert. Kept with the
// photos it was about, so it disappears as soon as any photo is replaced.
const [detectError, setDetectError] =
useState<{ message: string; photos: (string | null)[] } | null>(null)

// Height drives the pixel-to-millimetre calibration. A missing value
// means the millimetre parameters cannot be computed at all; a wrong
// one (170 typed as 17) is worse, because every millimetre reading
// then comes out confidently scaled by the wrong factor with no error
// raised anywhere. Bound it to a plausible human range.
const heightNumber = Number(patientHeightCm)

const isHeightValid =
patientHeightCm.trim() !== "" &&
Number.isFinite(heightNumber) &&
heightNumber >= 50 &&
heightNumber <= 250

// Age goes to the report as an integer, and the report endpoint refuses an
// empty one (FastAPI 0.115, checked 11 October 2026). Before this check the
// refusal came only after the clinician had finished the whole landmark
// review, and going back to fix the form threw that review away.
const ageNumber = Number(age)

const isAgeValid =
age.trim() !== "" &&
Number.isInteger(ageNumber) &&
ageNumber >= 1 &&
ageNumber <= 120

const shownError =
detectError &&
detectError.photos[0] === frontImage &&
detectError.photos[1] === sideImage &&
detectError.photos[2] === backImage
  ? detectError.message
  : null

const missing = [
  patientName.trim() === "" ? "name" : null,
  !isAgeValid ? "age" : null,
  !isHeightValid ? "height" : null,
  !frontImage ? "front photo" : null,
  !sideImage ? "side photo" : null,
  !backImage ? "back photo" : null,
].filter((m): m is string => m !== null)

const handleAnalyze = async () => {
if (
!frontFile ||
!sideFile ||
!backFile
) {
alert(
"Please upload front, side and back images."
)
return
}

try {
  setLoading(true)
  setDetectError(null)

  const result = await detectLandmarks({ frontFile, sideFile, backFile })

  setDetection(result)

  setStep("review")

} catch (error) {

  console.error(error)

  const message = error instanceof Error ? error.message : String(error)
  // The server names the view and the reason, for example
  // "Front image: pose detection failed: No person detected".
  const noPerson = message.match(/^(Front|Side|Back) image: pose detection failed: No person detected/i)
  setDetectError({
    message: noPerson
      ? `No person was found in the ${noPerson[1].toLowerCase()} photo. Retake it with the whole body in frame.`
      : `The photos could not be analysed: ${message}`,
    photos: [frontImage, sideImage, backImage],
  })

} finally {

  setLoading(false)
}

}

const [pdfBusy, setPdfBusy] = useState(false)

// Clears everything for the next patient. Was inline on the old
// "Start Over" button; now the report's "New assessment" action.
const resetAll = () => {

                setFrontImage(
                  null
                )
                setSideImage(
                  null
                )
                setBackImage(
                  null
                )

                setFrontFile(
                  null
                )
                setSideFile(
                  null
                )
                setBackFile(
                  null
                )

                setFrontSource("unknown")
                setSideSource("unknown")
                setBackSource("unknown")

                setPatientName("")
                setAge("")
                setGender("")
                setCaseRef("")
                setPatientHeightCm("")
                setClinicianName("")

                setReport(
                  null
                )

                setDetection(
                  null
                )

                setStep(
                  "upload"
                )
              }

const handleConfirm = async (review: LandmarkReviewSubmission) => {
if (!detection) return

try {
  setLoading(true)

  const result = await generateReport({
    detection,
    review,
    patientName,
    age,
    gender,
    caseRef,
    patientHeightCm,
    clinicianName,
    frontSource,
    sideSource,
    backSource,
  })

  setReport(result)

  setStep("report")

} catch (error) {

  console.error(error)

  alert(
    "Report failed: " +
      (error instanceof Error ? error.message : String(error)),
  )

} finally {

  setLoading(false)
}

}

return ( <div className="min-h-screen bg-[#F8F4EA]">

  <Header step={step} />

  <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8">

    {step === "upload" && (
      <section className="mx-auto w-full max-w-3xl pb-28 sm:pb-0">
        <header>
          <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[#5D6380]">
            New assessment
          </p>
          <h1 className="mt-1 font-display text-[26px] font-extrabold leading-tight tracking-tight text-[#141A33]">
            Patient and photographs
          </h1>
          <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-[#5D6380]">
            Fill in the patient&apos;s details, then take the three photographs. You will check
            the landmarks before any report is made.
          </p>
        </header>

        <div className="mt-6 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-5 sm:p-6">
          <h2 className="font-display text-[17px] font-bold text-[#141A33]">Patient</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Name">
              <input type="text" value={patientName} onChange={(e) => setPatientName(e.target.value)} className={INPUT_CLASS} autoComplete="off" />
            </Field>
            <Field
              label="Age"
              error={age.trim() !== "" && !isAgeValid ? "Enter a whole number between 1 and 120." : null}
            >
              <input type="number" inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} className={INPUT_CLASS} />
            </Field>
            <Field
              label="Height (cm)"
              hint="Used to turn the photo into millimetres. Measure it, do not ask."
              error={patientHeightCm.trim() !== "" && !isHeightValid ? "Enter the height in centimetres, between 50 and 250." : null}
            >
              <input type="number" inputMode="decimal" value={patientHeightCm} onChange={(e) => setPatientHeightCm(e.target.value)} className={INPUT_CLASS} />
            </Field>
            <Field label="Gender (optional)">
              <select value={gender} onChange={(e) => setGender(e.target.value)} className={INPUT_CLASS}>
                <option value="">Not given</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </Field>
            <Field label="Case reference (optional)">
              <input type="text" value={caseRef} onChange={(e) => setCaseRef(e.target.value)} className={INPUT_CLASS} autoComplete="off" />
            </Field>
            <Field label="Clinician (optional)">
              <input type="text" value={clinicianName} onChange={(e) => setClinicianName(e.target.value)} className={INPUT_CLASS} />
            </Field>
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-5 sm:p-6">
          <h2 className="font-display text-[17px] font-bold text-[#141A33]">Photographs</h2>
          <p className="mt-1 text-[14px] leading-relaxed text-[#5D6380]">
            The camera only takes the photo when the phone is level. An uploaded photo is measured
            the same way, but the report marks it as not checked.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <UploadZone label="Front" view="front" setImage={setFrontImage} setImageFile={setFrontFile} setSource={setFrontSource} />
            <UploadZone label="Side" view="side" setImage={setSideImage} setImageFile={setSideFile} setSource={setSideSource} />
            <UploadZone label="Back" view="back" setImage={setBackImage} setImageFile={setBackFile} setSource={setBackSource} />
          </div>
          <details className="mt-4 rounded-xl bg-[#F3EEE2] px-4 py-3 text-[13px] leading-relaxed text-[#5D6380]">
            <summary className="cursor-pointer font-medium text-[#141A33]">What makes a good photo?</summary>
            <p className="mt-2">
              The whole body in frame from head to feet, the camera level and at about half the
              patient&apos;s height, the same distance each visit, and clothing that leaves the
              shoulders, hips, knees and ankles visible. A screenshot or a photo of a screen will not
              measure correctly.
            </p>
          </details>
        </div>

        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-[#E3DCCB] bg-white/95 px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-md sm:static sm:mt-6 sm:border-0 sm:bg-transparent sm:p-0 sm:backdrop-blur-none">
          <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-end sm:gap-4">
            {shownError && !loading && (
              <p role="alert" className="rounded-xl border border-[#F2C9C5] bg-[#FDF1F0] px-3 py-2 text-center text-[13px] text-[#8C1D18] sm:text-right">
                {shownError}
              </p>
            )}
            {missing.length > 0 && !loading && (
              <p className="text-center text-[13px] text-[#5D6380] sm:text-right">
                Still needed: {missing.join(", ")}
              </p>
            )}
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={missing.length > 0 || loading}
              className="h-12 rounded-xl bg-[#4E888F] px-6 text-[15px] font-semibold text-white transition hover:bg-[#3B6A70] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? "Finding landmarks..." : "Continue to landmark check"}
            </button>
          </div>
        </div>
      </section>
    )}

    {step === "review" && detection && (
      <LandmarkReview
        detection={detection}
        loading={loading}
        onBack={() => {
          setDetection(null)
          setStep("upload")
        }}
        onConfirm={handleConfirm}
      />
    )}

    {step === "report" &&
      report && (
        <section className="mx-auto w-full max-w-4xl space-y-4">

          <ReportCard
            data={report}
          />

          {/* Actions in a bar that stays at the bottom of the screen while
              the report is read, and settles under the report at its end.
              At the top (before 12 October) they asked for a download
              before the report had been read; only at the end, a phone
              user scrolled ten screens to reach them. */}
          <div className="no-print sticky bottom-0 z-20 -mx-4 border-t border-[#E3DCCB] bg-[#FFFDF7]/95 px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border">
            <div className="mx-auto flex max-w-4xl gap-2.5 sm:justify-end">
              <button
                type="button"
                onClick={resetAll}
                className="h-11 flex-1 rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-4 text-[14px] font-semibold text-[#141A33] transition hover:bg-[#F3EEE2] sm:flex-none"
              >
                New assessment
              </button>
              <button
                type="button"
                disabled={pdfBusy}
                onClick={async () => {
                  setPdfBusy(true)
                  try {
                    await downloadPostureReportPdf(report)
                  } catch {
                    alert("Could not generate the report PDF. Please try again.")
                  } finally {
                    setPdfBusy(false)
                  }
                }}
                className="h-11 flex-1 rounded-xl bg-[#4E888F] px-5 text-[14px] font-semibold text-white transition hover:bg-[#3B6A70] disabled:opacity-60 sm:flex-none"
              >
                {pdfBusy ? "Preparing PDF…" : "Download PDF"}
              </button>
            </div>
          </div>

        </section>
      )}

  </main>
</div>

)
}
