const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"

import type { PostureReport } from "@/types/posture"

interface AnalyzePosturePayload {
frontFile: File
sideFile: File
backFile: File

patientName: string
age: string
gender: string
caseRef: string
patientHeightCm: string
clinicianName: string
}

export async function analyzePosture(
payload: AnalyzePosturePayload,
): Promise<PostureReport> {

const formData = new FormData()

formData.append(
"front_image",
payload.frontFile,
)

formData.append(
"side_image",
payload.sideFile,
)

formData.append(
"back_image",
payload.backFile,
)

formData.append(
"patient_name",
payload.patientName,
)

formData.append(
"age",
payload.age,
)

formData.append(
"gender",
payload.gender,
)

formData.append(
"case_ref",
payload.caseRef,
)

if (payload.patientHeightCm) {
formData.append(
"patient_height_cm",
payload.patientHeightCm,
)
}

if (payload.clinicianName) {
formData.append(
"clinician_name",
payload.clinicianName,
)
}

const response = await fetch(
`${API_URL}/posture/analyze`,
{
method: "POST",
body: formData,
},
)

if (!response.ok) {
throw new Error(
"Failed to analyze posture",
)
}

return response.json()
}


/**
 * Request the server-rendered clinical PDF for an already-computed report.
 *
 * The report used to be "exported" with window.print(), which printed the
 * on-screen dashboard: the browser stamped its own URL and timestamp on every
 * page, interactive buttons appeared in the patient's copy, and measurements
 * landed on a different page from the image they were derived from. The PDF
 * is now rendered server-side from a layout designed for paper.
 */
export async function downloadPostureReportPdf(
  report: PostureReport,
): Promise<void> {

  const response = await fetch(
    `${API_URL}/posture/report/pdf`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(report),
    },
  )

  if (!response.ok) {
    throw new Error(
      "Failed to generate report PDF",
    )
  }

  const blob = await response.blob()

  const patientName = report.patient?.name ?? ""

  const safeName =
    patientName
      .split("")
      .filter((c) => /[a-zA-Z0-9\-_]/.test(c))
      .join("") || "report"

  const url = window.URL.createObjectURL(blob)

  const link = document.createElement("a")
  link.href = url
  link.download = `posture-assessment-${safeName}.pdf`

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  window.URL.revokeObjectURL(url)
}
