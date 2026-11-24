"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import type { CaptureLevel } from "@/lib/tilt"

import UploadZone from "@/components/posture/UploadZone"

import ReportCard from "@/components/report/ReportCard"
import WhatsAppShare from "@/components/report/WhatsAppShare"

import LandmarkReview from "@/components/review/LandmarkReview"

import AuthGate, { useSession } from "@/components/auth/AuthGate"

import PatientPicker, { ageSex } from "@/components/patient/PatientPicker"
import PreviousReports from "@/components/patient/PreviousReports"

import {
  ApiError,
  detectLandmarks,
  downloadPostureReportPdf,
  downloadSavedReportPdf,
  fetchPatient,
  fetchSavedReport,
  generateReport,
  type PickerPatient,
} from "@/lib/api"

import type { DetectionResult, LandmarkReviewSubmission, PostureReport } from "@/types/posture"
import { asset, toolUrl } from "@/lib/hub"

// "review" is the founders' landmark check (Q6, 10 October 2026): no report
// exists until the clinician has confirmed the points.
type Step = "upload" | "review" | "report"

// App bar, brand direction B (13 October 2026): the Midnight band of the AV
// Suite CRM with the white logo and the three steps of an assessment. The
// logo shows on every step since 17 November 2026: the report's letterhead
// now carries the clinic's logo, not Aarogya Virohan's, so step 3 no longer
// fell back to the name as text.
const STEP_ORDER: { key: Step; label: string }[] = [
  { key: "upload", label: "Patient & photos" },
  { key: "review", label: "Landmark check" },
  { key: "report", label: "Report" },
]

function Header({ step }: { step: Step }) {
  const current = STEP_ORDER.findIndex((s) => s.key === step)
  const { me, signOut } = useSession()
  const crmUrl = toolUrl("crm")
  const leave = () => {
    if (step !== "upload" && !window.confirm("Sign out? This assessment will be lost.")) return
    signOut()
  }
  return (
    <header className="bg-[linear-gradient(115deg,#0B1238_0%,#121F4A_60%,#1B4A54_100%)] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3.5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={asset("/brand/av_logo_wordmark_white.png")} alt="Aarogya Virohan" className="h-6 w-auto" />
        <span className="rounded-full bg-[#C1FF72] px-2.5 py-0.5 text-[11.5px] font-bold text-[#0B1238]">
          Posture Tool
        </span>
        <div className="ml-auto flex min-w-0 items-center gap-3 text-[12px] sm:order-last sm:ml-4">
          {crmUrl && (
            <a href={crmUrl} className="font-semibold text-[#C1FF72] underline-offset-2 hover:underline" data-testid="back-to-crm">
              Back to CRM
            </a>
          )}
          <span className="max-w-[160px] truncate text-[#C3C9E6]" title={me.user.email}>
            {me.clinic?.name ?? me.user.email}
          </span>
          <button type="button" onClick={leave} className="font-semibold text-white underline-offset-2 hover:underline">
            Sign out
          </button>
        </div>
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

// Required fields carry a red asterisk; their "is required" message shows
// only after the clinician has tried to continue (13 October 2026, in place
// of the "Still needed: ..." line beside the button).
function Field({
  label,
  required = false,
  hint,
  error,
  children,
}: {
  label: string
  required?: boolean
  hint?: React.ReactNode
  error?: string | null
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">
        {label}
        {required && (
          <span className="ml-0.5 text-[#B4231B]" aria-hidden="true">
            *
          </span>
        )}
      </span>
      {children}
      {error ? (
        <span role="alert" className="mt-1 block text-[12px] font-medium text-[#B4231B]">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-[12px] text-[#5D6380]">{hint}</span>
      ) : null}
    </label>
  )
}

// Short on purpose (Onkar, 13 October 2026). Every millimetre on the report
// is scaled from the height, so a guessed height moves every mm value.
function HeightHint() {
  return (
    <span className="flex items-start gap-1.5">
      <svg viewBox="0 0 16 16" className="mt-[1px] h-3.5 w-3.5 flex-none text-[#4E888F]" aria-hidden="true">
        <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M8 7.2v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="8" cy="4.9" r="0.9" fill="currentColor" />
      </svg>
      <span>Must be accurate. Every mm value depends on it.</span>
    </span>
  )
}

function Assessment() {
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
// existing file. An uploaded photo skips the tilt correction, framing and encoding
// protocol, so a measurement taken from one is not comparable with a
// guided capture of the same patient. The report records which it was.
type CaptureSource = "camera" | "upload" | "unknown"

const [frontSource, setFrontSource] =
useState<CaptureSource>("unknown")

const [sideSource, setSideSource] =
useState<CaptureSource>("unknown")

const [backSource, setBackSource] =
useState<CaptureSource>("unknown")

// Phone tilt at capture for each guided photo (lib/tilt.ts), corrected on
// the server. null for uploads and devices without a tilt sensor.
const [frontLevel, setFrontLevel] =
useState<CaptureLevel | null>(null)

const [sideLevel, setSideLevel] =
useState<CaptureLevel | null>(null)

const [backLevel, setBackLevel] =
useState<CaptureLevel | null>(null)

// The CRM patient (POS-2). Opened from the CRM patient page (?patient_id=...)
// the patient is loaded and locked; opened directly, one is picked from the
// clinic's patients. There is no free-text patient.
const searchParams = useSearchParams()
const crmPatientId = searchParams.get("patient_id")

const [patient, setPatient] =
useState<PickerPatient | null>(null)

const [patientLocked, setPatientLocked] =
useState(false)

const [patientLoading, setPatientLoading] =
useState(Boolean(crmPatientId))

const [patientError, setPatientError] =
useState<string | null>(null)

useEffect(() => {
  if (!crmPatientId) return
  let cancelled = false
  fetchPatient(crmPatientId)
    .then((p) => {
      if (cancelled) return
      setPatient(p)
      setPatientLocked(true)
      setPatientError(null)
    })
    .catch((e) => {
      if (cancelled) return
      const notFound = e instanceof ApiError && (e.status === 404 || e.status === 422)
      setPatient(null)
      setPatientLocked(false)
      setPatientError(
        notFound
          ? "This patient was not found in your clinic. Choose a patient below."
          : e instanceof Error
            ? e.message
            : "Could not load the patient.",
      )
    })
    .finally(() => {
      if (!cancelled) setPatientLoading(false)
    })
  return () => {
    cancelled = true
  }
}, [crmPatientId])

const [patientHeightCm, setPatientHeightCm] =
useState("")

const [clinicianName, setClinicianName] =
useState("")

// A report opened from the list of earlier reports: saved data, no photographs.
const [savedView, setSavedView] =
useState(false)

const [openingId, setOpeningId] =
useState<string | null>(null)

// Bumped after a report is saved, so the list of earlier reports reloads.
const [reportsVersion, setReportsVersion] =
useState(0)

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

// Name, age and sex come from the CRM record. A patient with no age there
// cannot be assessed; the clinician is told to add it in the CRM.
const patientAgeMissing = patient !== null && patient.age === null

// Set when the clinician presses Continue with something missing; until
// then no field is marked, so an empty form does not open full of errors.
const [showErrors, setShowErrors] =
useState(false)

const patientFieldError =
  showErrors && patient === null
    ? "Choose a patient"
    : patientAgeMissing
      ? "This patient has no age in the CRM. Add the date of birth or age in the CRM, then open Posture again."
      : null
const heightError =
  patientHeightCm.trim() !== "" && !isHeightValid
    ? "Enter the height in centimetres, between 50 and 250."
    : showErrors && patientHeightCm.trim() === ""
      ? "Height is required"
      : null
const photoError = (image: string | null, view: string) =>
  showErrors && !image ? `${view} photo is required` : null

const shownError =
detectError &&
detectError.photos[0] === frontImage &&
detectError.photos[1] === sideImage &&
detectError.photos[2] === backImage
  ? detectError.message
  : null

const missing = [
  patient === null || patientAgeMissing ? "patient" : null,
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
                setFrontLevel(null)
                setSideLevel(null)
                setBackLevel(null)

                // A patient opened from the CRM stays; a picked one is cleared.
                if (!patientLocked) setPatient(null)
                setSavedView(false)
                setPatientHeightCm("")
                setClinicianName("")
                setShowErrors(false)

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

const openSaved = async (reportId: string) => {
  setOpeningId(reportId)
  try {
    const saved = await fetchSavedReport(reportId)
    setReport(saved)
    setSavedView(true)
    setStep("report")
  } catch (error) {
    alert("Could not open the report: " + (error instanceof Error ? error.message : String(error)))
  } finally {
    setOpeningId(null)
  }
}

const handleConfirm = async (review: LandmarkReviewSubmission) => {
if (!detection || !patient) return

try {
  setLoading(true)

  const result = await generateReport({
    detection,
    review,
    patientId: patient?.id ?? "",
    patientHeightCm,
    clinicianName,
    frontSource,
    sideSource,
    backSource,
    frontLevel,
    sideLevel,
    backLevel,
  })

  setReport(result)
  setSavedView(false)
  setReportsVersion((v) => v + 1)

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
            Patient details &amp; photographs
          </h1>
          <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-[#5D6380]">
            Enter the patient&apos;s details, then take three photographs: front, side and back.
          </p>
        </header>

        <div className="mt-6 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-5 sm:p-6">
          <h2 className="font-display text-[17px] font-bold text-[#141A33]">Patient</h2>

          {patientLoading ? (
            <p className="mt-4 text-[14px] text-[#5D6380]" data-testid="patient-loading">Loading patient...</p>
          ) : patient ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#E3DCCB] bg-[#F8F4EA] px-4 py-3" data-testid="patient-card">
              <div className="min-w-0">
                <p className="truncate text-[16px] font-semibold text-[#141A33]" data-testid="patient-name">{patient.name}</p>
                <p className="mt-0.5 text-[13px] text-[#5D6380]">
                  Patient ID <span className="font-mono font-semibold text-[#141A33]" data-testid="patient-case-id">{patient.caseId}</span>
                  {" · "}
                  {ageSex(patient)}
                </p>
              </div>
              {patientLocked ? (
                <span className="rounded-full bg-[#E4EFEF] px-2.5 py-1 text-[11.5px] font-semibold text-[#2F5A60]" data-testid="patient-locked">
                  From the CRM
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => setPatient(null)}
                  className="h-9 rounded-lg border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[13px] font-semibold text-[#141A33] transition hover:bg-[#F3EEE2]"
                  data-testid="patient-change"
                >
                  Change patient
                </button>
              )}
            </div>
          ) : (
            <div className="mt-4">
              {patientError && (
                <p role="alert" className="mb-3 rounded-xl border border-[#F2C9C5] bg-[#FDF1F0] px-3 py-2 text-[13px] text-[#8C1D18]">
                  {patientError}
                </p>
              )}
              <PatientPicker onSelect={(p) => { setPatient(p); setPatientError(null) }} error={patientFieldError} />
            </div>
          )}
          {patient && patientFieldError && (
            <p role="alert" className="mt-2 text-[12px] font-medium text-[#B4231B]">{patientFieldError}</p>
          )}

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Height (cm)" required hint={<HeightHint />} error={heightError}>
              <input type="number" inputMode="decimal" value={patientHeightCm} onChange={(e) => setPatientHeightCm(e.target.value)} className={INPUT_CLASS} />
            </Field>
            <Field label="Clinician">
              <input type="text" value={clinicianName} onChange={(e) => setClinicianName(e.target.value)} className={INPUT_CLASS} />
            </Field>
          </div>
        </div>

        {patient && (
          <PreviousReports patientId={patient.id} version={reportsVersion} onOpen={openSaved} busyId={openingId} />
        )}

        <div className="mt-4 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-5 sm:p-6">
          <h2 className="font-display text-[17px] font-bold text-[#141A33]">Photographs</h2>
          <p className="mt-1 text-[14px] leading-relaxed text-[#5D6380]">
            The camera measures how the phone is tilted and corrects for it. An uploaded photo is
            measured the same way, but without that correction, and the report marks it.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <UploadZone label="Front" view="front" required error={photoError(frontImage, "Front")} setImage={setFrontImage} setImageFile={setFrontFile} setSource={setFrontSource} setLevel={setFrontLevel} />
            <UploadZone label="Side" view="side" required error={photoError(sideImage, "Side")} setImage={setSideImage} setImageFile={setSideFile} setSource={setSideSource} setLevel={setSideLevel} />
            <UploadZone label="Back" view="back" required error={photoError(backImage, "Back")} setImage={setBackImage} setImageFile={setBackFile} setSource={setBackSource} setLevel={setBackLevel} />
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

        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-[#E3DCCB] bg-[#FFFDF7]/95 px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-md sm:static sm:mt-6 sm:border-0 sm:bg-transparent sm:p-0 sm:backdrop-blur-none">
          <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-end sm:gap-4">
            {shownError && !loading && (
              <p role="alert" className="rounded-xl border border-[#F2C9C5] bg-[#FDF1F0] px-3 py-2 text-center text-[13px] text-[#8C1D18] sm:text-right">
                {shownError}
              </p>
            )}
            {showErrors && missing.length > 0 && !loading && (
              <p role="alert" className="text-center text-[13px] font-medium text-[#B4231B] sm:text-right">
                Fill in the fields marked in red to continue.
              </p>
            )}
            <button
              type="button"
              onClick={() => {
                if (missing.length > 0) {
                  setShowErrors(true)
                  // Bring the first missing field into view, so on a phone
                  // the clinician sees what is wrong, not just the button.
                  requestAnimationFrame(() => {
                    document.querySelector('[role="alert"]')?.scrollIntoView({ behavior: "smooth", block: "center" })
                  })
                  return
                }
                void handleAnalyze()
              }}
              disabled={loading}
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

          {savedView && (
            <p className="no-print rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-4 py-2.5 text-[13px] text-[#5D6380]" data-testid="saved-note">
              Saved report. Photographs are not stored with saved reports; the measurements and findings are as they were on the day.
            </p>
          )}

          <ReportCard
            data={report}
          />

          {/* Actions in a bar that stays at the bottom of the screen while
              the report is read, and settles under the report at its end.
              At the top (before 12 October) they asked for a download
              before the report had been read; only at the end, a phone
              user scrolled ten screens to reach them. */}
          <div className="no-print sticky bottom-0 z-20 -mx-4 border-t border-[#E3DCCB] bg-[#FFFDF7]/95 px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border">
            <div className="mx-auto flex max-w-4xl flex-wrap gap-2.5 sm:justify-end">
              <button
                type="button"
                onClick={resetAll}
                className="h-11 flex-1 rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] whitespace-nowrap px-2 text-[13px] sm:px-4 sm:text-[14px] font-semibold text-[#141A33] transition hover:bg-[#F3EEE2] sm:flex-none"
              >
                {savedView ? "Back" : "New assessment"}
              </button>
              <WhatsAppShare report={report} />
              <button
                type="button"
                disabled={pdfBusy}
                onClick={async () => {
                  setPdfBusy(true)
                  try {
                    if (savedView && report.reportId) {
                      await downloadSavedReportPdf(report.reportId, report.patient?.name ?? "")
                    } else {
                      await downloadPostureReportPdf(report)
                    }
                  } catch {
                    alert("Could not generate the report PDF. Please try again.")
                  } finally {
                    setPdfBusy(false)
                  }
                }}
                className="h-11 flex-1 rounded-xl bg-[#4E888F] whitespace-nowrap px-2 text-[13px] sm:px-4 sm:text-[14px] font-semibold text-white transition hover:bg-[#3B6A70] disabled:opacity-60 sm:flex-none"
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

// Signed-in only (U1, 14 November 2026). Also served at /analyze, the
// address the CRM patient page opens.
export default function Page() {
  return (
    <AuthGate>
      <Suspense fallback={null}>
        <Assessment />
      </Suspense>
    </AuthGate>
  )
}
