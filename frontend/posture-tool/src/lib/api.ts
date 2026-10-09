const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"

import type {
  DetectionResult,
  LandmarkReviewSubmission,
  PostureReport,
} from "@/types/posture"

// The server explains a refused review (a point not reviewed, an expired
// detection) in its error detail; show that rather than a generic failure.
async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === "string") return body.detail
  } catch {
    // not JSON
  }
  return fallback
}

/**
 * Step one of the landmark review: detection only. Nothing is measured or
 * graded until the clinician confirms the points.
 */
export async function detectLandmarks(files: {
  frontFile: File
  sideFile: File
  backFile: File
}): Promise<DetectionResult> {
  const formData = new FormData()
  formData.append("front_image", files.frontFile)
  formData.append("side_image", files.sideFile)
  formData.append("back_image", files.backFile)

  const response = await fetch(`${API_URL}/posture/detect`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await errorDetail(response, "Landmark detection failed"))
  }

  return response.json()
}

async function dataUrlToBlob(dataUrl: string): Promise<Blob> {
  const response = await fetch(dataUrl)
  return response.blob()
}

interface ReportPayload {
  detection: DetectionResult
  review: LandmarkReviewSubmission
  patientName: string
  age: string
  gender: string
  caseRef: string
  patientHeightCm: string
  clinicianName: string
  frontSource: string
  sideSource: string
  backSource: string
}

/**
 * Step two: the report, built only from the points the clinician confirmed.
 * The full photographs are not sent again; the display copies from
 * detection go back for the annotated images.
 */
export async function generateReport(payload: ReportPayload): Promise<PostureReport> {
  const { detection } = payload
  const formData = new FormData()

  formData.append("detection_token", detection.detectionToken)
  formData.append("review", JSON.stringify(payload.review))
  formData.append("front_display", await dataUrlToBlob(detection.views.front.displayImage), "front.jpg")
  formData.append("side_display", await dataUrlToBlob(detection.views.side.displayImage), "side.jpg")
  formData.append("back_display", await dataUrlToBlob(detection.views.back.displayImage), "back.jpg")

  formData.append("patient_name", payload.patientName)
  formData.append("age", payload.age)
  formData.append("gender", payload.gender)
  formData.append("case_ref", payload.caseRef)
  formData.append("patient_height_cm", payload.patientHeightCm)
  formData.append("clinician_name", payload.clinicianName)
  formData.append("front_source", payload.frontSource)
  formData.append("side_source", payload.sideSource)
  formData.append("back_source", payload.backSource)

  const response = await fetch(`${API_URL}/posture/report`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await errorDetail(response, "Report generation failed"))
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
