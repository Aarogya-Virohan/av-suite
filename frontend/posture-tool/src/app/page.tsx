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
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-7xl items-center px-4 py-4">
        <span className="text-lg font-semibold text-slate-900">
          Arogya Virohan
        </span>
      </div>
    </header>
  )
}

export default function Page() {

  const [step, setStep] =
    useState<Step>("upload")

  const [image, setImage] =
    useState<string | null>(null)

  const [imageFile, setImageFile] =
    useState<File | null>(null)

  const [report, setReport] =
    useState<PostureReport | null>(null)

  const [loading, setLoading] =
    useState(false)

  const handleAnalyze = async () => {

    if (!imageFile) return

    try {

      setLoading(true)

      const result = await analyzePosture(
        imageFile
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

  return (
    <div className="min-h-screen bg-slate-100">

      {/* Header */}
      <Header />

      {/* Main */}
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8">

        {/* =========================
            UPLOAD STEP
        ========================== */}

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

              {/* Upload */}
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

                <h2 className="text-xl font-semibold text-slate-900">
                  Upload Patient Image
                </h2>

                <p className="mt-2 text-slate-600">
                  Use a clear standing posture photograph with
                  shoulders, spine, pelvis, and knees visible.
                </p>

                <div className="mt-6">

                  <UploadZone
                    setImage={setImage}
                    setImageFile={setImageFile}
                  />

                </div>

              </div>

              {/* Preview */}
              <div className="rounded-2xl border border-slate-200 bg-white p-6">

                <h2 className="text-xl font-semibold text-slate-900">
                  Image Preview
                </h2>

                <p className="mt-2 text-slate-600">
                  Uploaded posture image preview before analysis.
                </p>

                <div className="mt-6">
                  <ImagePreview image={image} />
                </div>

              </div>
            </div>

            {/* Loading */}
            {loading && (
              <p className="mt-6 text-slate-600">
                Running posture analysis...
              </p>
            )}

            {/* CTA */}
            <div className="mt-8 flex justify-end">

              <button
                type="button"
                onClick={handleAnalyze}
                disabled={!image || loading}
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

        {/* =========================
            ANALYSIS STEP
        ========================== */}

        {step === "analysis" && (
          <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">

              <div>

                <h1 className="text-4xl font-bold tracking-tight text-slate-900">
                  Analysis Results
                </h1>

                <p className="mt-3 text-lg text-slate-600">
                  Review the detected biomechanical deviations
                  before generating the production report.
                </p>

              </div>

              <button
                type="button"
                onClick={() => setStep("upload")}
                className="
                  rounded-full
                  border
                  border-slate-300
                  px-5
                  py-3
                  text-slate-700
                  transition
                  hover:bg-slate-100
                "
              >
                Change Image
              </button>

            </div>

            <div className="mt-8">
              <AnalysisPanel />
            </div>

            <div className="mt-8 flex justify-end">

              <button
                type="button"
                onClick={() => setStep("report")}
                className="
                  rounded-full
                  bg-slate-900
                  px-6
                  py-3
                  text-white
                  transition
                  hover:bg-slate-800
                "
              >
                Generate Clinical Report
              </button>

            </div>

          </section>
        )}

        {/* =========================
            REPORT STEP
        ========================== */}

        {step === "report" && report && (
          <section className="space-y-6">

            {/* Report */}
            <ReportCard data={report} />

            {/* Actions */}
            <div className="flex flex-wrap gap-4">

              <button
                type="button"
                onClick={() => window.print()}
                className="
                  rounded-full
                  bg-slate-900
                  px-6
                  py-3
                  text-white
                  transition
                  hover:bg-slate-800
                "
              >
                Export Report
              </button>

              <button
                type="button"
                onClick={() => {
                  setImage(null)
                  setImageFile(null)
                  setReport(null)
                  setStep("upload")
                }}
                className="
                  rounded-full
                  border
                  border-slate-300
                  bg-white
                  px-6
                  py-3
                  text-slate-700
                  transition
                  hover:bg-slate-100
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