"use client"

import { useState } from "react"
import Header from "@/src/components/layout/Header"
import AnalysisPanel from "@/src/components/posture/AnalysisPanel"
import ImagePreview from "@/src/components/posture/ImagePreview"
import UploadZone from "@/src/components/posture/UploadZone"
import data from "@/src/data/mockAnalysis.json"

type Step = "upload" | "analysis" | "report"

export default function Page() {
  const [step, setStep] = useState<Step>("upload")
  const [image, setImage] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-slate-100">
      <Header />

      <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8">
        {step === "upload" && (
          <section className="rounded-2xl bg-white p-6 shadow-sm">
            <h1 className="text-3xl font-semibold text-slate-900">Upload posture image</h1>
            <p className="mt-2 text-slate-600">
              Start by selecting a front or side posture photo for analysis.
            </p>

            <div className="mt-6">
              <UploadZone setImage={setImage} />
            </div>

            <ImagePreview image={image} />

            <button
              type="button"
              onClick={() => setStep("analysis")}
              disabled={!image}
              className="mt-6 rounded-full bg-slate-900 px-5 py-3 text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Analyse Posture
            </button>
          </section>
        )}

        {step === "analysis" && (
          <section className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-slate-900">Analysis results</h1>
                <p className="mt-2 text-slate-600">
                  Review the posture findings before generating the report.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setStep("upload")}
                className="rounded-full border border-slate-300 px-4 py-2 text-sm text-slate-700"
              >
                Change Image
              </button>
            </div>

            <div className="mt-6">
              <AnalysisPanel />
            </div>

            <button
              type="button"
              onClick={() => setStep("report")}
              className="mt-6 rounded-full bg-slate-900 px-5 py-3 text-white"
            >
              Generate Report
            </button>
          </section>
        )}

        {step === "report" && (
          <section className="rounded-2xl bg-white p-6 shadow-sm">
            <h1 className="text-3xl font-semibold text-slate-900">Posture report</h1>
            <p className="mt-2 text-slate-600">
              This is a simple summary view until dedicated report components are added.
            </p>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4">
                <h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
                  Patient
                </h2>
                <p className="mt-2 text-lg font-semibold text-slate-900">{data.patientName}</p>
                <p className="text-slate-600">Age {data.patientAge}</p>
                <p className="text-slate-600">{data.date}</p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4">
                <h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
                  Overall Score
                </h2>
                <p className="mt-2 text-4xl font-bold text-slate-900">{data.overallScore}</p>
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-slate-200 p-4">
              <h2 className="text-lg font-semibold text-slate-900">Recommendations</h2>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                {data.recommendations.map((recommendation) => (
                  <li key={recommendation}>{recommendation}</li>
                ))}
              </ul>
            </div>

            <div className="mt-6 rounded-xl border border-slate-200 p-4">
              <h2 className="text-lg font-semibold text-slate-900">Therapist Notes</h2>
              <p className="mt-3 text-slate-700">{data.therapistNotes}</p>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => window.print()}
                className="rounded-full bg-slate-900 px-5 py-3 text-white"
              >
                Export Report
              </button>

              <button
                type="button"
                onClick={() => {
                  setImage(null)
                  setStep("upload")
                }}
                className="rounded-full border border-slate-300 px-5 py-3 text-slate-700"
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
