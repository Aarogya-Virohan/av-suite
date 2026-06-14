"use client"

import { useState } from "react"

import UploadZone from "@/components/posture/UploadZone"
import ImagePreview from "@/components/posture/ImagePreview"
import AnalysisPanel from "@/components/posture/AnalysisPanel"

import ReportCard from "@/components/report/ReportCard"

import { analyzePosture } from "@/lib/api"

import type { PostureReport } from "@/types/posture"

type Step = "upload" | "analysis" | "report"

function Header() {
return ( <header className="border-b border-slate-200 bg-white"> <div className="mx-auto flex w-full max-w-7xl items-center px-4 py-4"> <span className="text-lg font-semibold text-slate-900">
Arogya Virohan </span> </div> </header>
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

const [report, setReport] =
useState<PostureReport | null>(null)

const [loading, setLoading] =
useState(false)

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

  const result =
    await analyzePosture(
       {
         frontFile,
         sideFile,
         backFile,
         patientName,
         age,
         gender,
         caseRef,
         patientHeightCm,
       }
    )

  setReport(result)

  setStep("analysis")

} catch (error) {

  console.error(error)

  alert("Analysis failed")

} finally {

  setLoading(false)
}

}

return ( <div className="min-h-screen bg-slate-100">

  <Header />

  <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8">

    {step === "upload" && (
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

        <div className="max-w-2xl">

          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            Clinical Posture Assessment
          </h1>

          <p className="mt-3 text-lg text-slate-600">
            Upload patient posture images to generate a
            multi-plane biomechanical analysis report.
          </p>

        </div>

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

            <h2 className="text-xl font-semibold text-slate-900">
              Patient Intake
            </h2>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">

              <input
                type="text"
                placeholder="Patient Name"
                value={patientName}
                onChange={(e) =>
                  setPatientName(
                    e.target.value
                  )
                }
                className="rounded-xl border p-3"
              />

              <input
                type="number"
                placeholder="Age"
                value={age}
                onChange={(e) =>
                  setAge(
                    e.target.value
                  )
                }
                className="rounded-xl border p-3"
              />

              <input
                type="text"
                placeholder="Gender"
                value={gender}
                onChange={(e) =>
                  setGender(
                    e.target.value
                  )
                }
                className="rounded-xl border p-3"
              />

              <input
                type="text"
                placeholder="Case Reference"
                value={caseRef}
                onChange={(e) =>
                  setCaseRef(
                    e.target.value
                  )
                }
                className="rounded-xl border p-3"
              />

              <input
                type="number"
                placeholder="Height (cm)"
                value={patientHeightCm}
                onChange={(e) =>
                  setPatientHeightCm(
                    e.target.value
                  )
                }
                className="rounded-xl border p-3"
              />

            </div>

            <div className="mt-8 space-y-4">

              <UploadZone
                label="Front View"
                setImage={
                  setFrontImage
                }
                setImageFile={
                  setFrontFile
                }
              />

              <UploadZone
                label="Side View"
                setImage={
                  setSideImage
                }
                setImageFile={
                  setSideFile
                }
              />

              <UploadZone
                label="Back View"
                setImage={
                  setBackImage
                }
                setImageFile={
                  setBackFile
                }
              />

            </div>

          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6">

            <h2 className="text-xl font-semibold text-slate-900">
              Image Preview
            </h2>

            <div className="mt-6 space-y-4">

              <ImagePreview
                image={frontImage}
              />

              <ImagePreview
                image={sideImage}
              />

              <ImagePreview
                image={backImage}
              />

            </div>

          </div>

        </div>

        {loading && (
          <p className="mt-6 text-slate-600">
            Running posture analysis...
          </p>
        )}

        <div className="mt-8 flex justify-end">

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={
              !frontImage ||
              !sideImage ||
              !backImage ||
              loading
            }
            className="
              rounded-full
              bg-slate-900
              px-6
              py-3
              text-white
              transition
              hover:bg-slate-800
              disabled:cursor-not-allowed
              disabled:bg-slate-300
            "
          >
            {loading
              ? "Analysing..."
              : "Analyse Posture"}
          </button>

        </div>

      </section>
    )}

    {step === "analysis" && (
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">

          <div>

            <h1 className="text-4xl font-bold tracking-tight text-slate-900">
              Analysis Results
            </h1>

            <p className="mt-3 text-lg text-slate-600">
              Review the detected biomechanical deviations.
            </p>

          </div>

          <button
            type="button"
            onClick={() =>
              setStep("upload")
            }
            className="
              rounded-full
              border
              border-slate-300
              px-5
              py-3
              text-slate-700
            "
          >
            Change Images
          </button>

        </div>

        <div className="mt-8">
          <AnalysisPanel />
        </div>

        <div className="mt-8 flex justify-end">

          <button
            type="button"
            onClick={() =>
              setStep("report")
            }
            className="
              rounded-full
              bg-slate-900
              px-6
              py-3
              text-white
            "
          >
            Generate Clinical Report
          </button>

        </div>

      </section>
    )}

    {step === "report" &&
      report && (
        <section className="space-y-6">

          <ReportCard
            data={report}
          />

          <div className="flex flex-wrap gap-4">

            <button
              type="button"
              onClick={() =>
                window.print()
              }
              className="
                rounded-full
                bg-slate-900
                px-6
                py-3
                text-white
              "
            >
              Export Report
            </button>

            <button
              type="button"
              onClick={() => {

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

                setPatientName("")
                setAge("")
                setGender("")
                setCaseRef("")
                setPatientHeightCm("")

                setReport(
                  null
                )

                setStep(
                  "upload"
                )
              }}
              className="
                rounded-full
                border
                border-slate-300
                bg-white
                px-6
                py-3
                text-slate-700
              "
            >
              Start Over
            </button>

          </div>

        </section>
      )}

  </main>
</div>

)
}
