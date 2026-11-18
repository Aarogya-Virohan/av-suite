const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
const API = `${BASE_URL}/api/v1`

import type {
  DetectionResult,
  LandmarkReviewSubmission,
  PostureReport,
} from "@/types/posture"
import type { CaptureLevel } from "@/lib/tilt"

// ------------------------------------------------------------------ session
// Same storage keys as the Exercise Library. Each app runs on its own origin,
// so the clinician signs in to each one separately.

const TOKEN_KEY = "token"
const EMAIL_KEY = "userEmail"

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function getSavedEmail(): string {
  if (typeof window === "undefined") return ""
  try {
    return localStorage.getItem(EMAIL_KEY) ?? ""
  } catch {
    return ""
  }
}

export function setSession(token: string, email: string) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(EMAIL_KEY, email)
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
  } catch {
    // storage blocked: nothing to clear
  }
}

/** The workspace (clinic) the current token was issued for, read from its claims. */
export function tokenClinicId(token: string | null = getToken()): string | null {
  if (!token) return null
  try {
    const part = token.split(".")[1]
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"))
    const claims = JSON.parse(json) as { clinic_id?: unknown }
    return typeof claims.clinic_id === "string" ? claims.clinic_id : null
  } catch {
    return null
  }
}

// ------------------------------------------------------------------ errors

export interface WorkspaceOption {
  clinic_id: string
  name: string
  role?: string
}

/**
 * Error from the API with the backend's message. The backend sends
 * detail: "text", detail: {code, message, workspaces} (for example
 * WORKSPACE_SELECTION_REQUIRED), detail: [...] (validation) or
 * meta.error.{code, message} (the envelope).
 */
export class ApiError extends Error {
  status: number
  code?: string
  workspaces?: WorkspaceOption[]

  constructor(message: string, status: number, code?: string, workspaces?: WorkspaceOption[]) {
    super(message)
    this.status = status
    this.code = code
    this.workspaces = workspaces
  }
}

function friendlyStatus(status: number): string {
  if (status === 401) return "Your session has ended. Please sign in again."
  if (status === 403) return "You do not have access to this."
  if (status === 404) return "Not found."
  if (status >= 500) return "The server ran into a problem. Please try again."
  return "Something went wrong. Please try again."
}

async function toApiError(response: Response, fallback?: string): Promise<ApiError> {
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // not JSON
  }
  const b = body as {
    detail?: unknown
    message?: unknown
    meta?: { error?: { message?: unknown; code?: unknown } }
  } | null
  const detail = b?.detail

  let message: string | undefined
  let code: string | undefined
  let workspaces: WorkspaceOption[] | undefined

  if (typeof detail === "string") {
    message = detail
  } else if (Array.isArray(detail)) {
    // FastAPI validation errors: name the field so the failure is not silent.
    message = detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "request"
        return `${String(field)}: ${d.msg ?? "invalid"}`
      })
      .join("; ")
  } else if (detail && typeof detail === "object") {
    const d = detail as { message?: unknown; code?: unknown; workspaces?: unknown }
    if (typeof d.message === "string") message = d.message
    if (typeof d.code === "string") code = d.code
    if (Array.isArray(d.workspaces)) {
      workspaces = d.workspaces.filter(
        (w): w is WorkspaceOption =>
          !!w &&
          typeof (w as WorkspaceOption).clinic_id === "string" &&
          typeof (w as WorkspaceOption).name === "string",
      )
    }
  }
  if (!message && typeof b?.meta?.error?.message === "string") message = b.meta.error.message
  if (!code && typeof b?.meta?.error?.code === "string") code = b.meta.error.code
  if (!message && typeof b?.message === "string") message = b.message

  // Plain words for the two ways a signed-in clinician can be refused.
  if (response.status === 403 && code === "PRODUCT_NOT_ENTITLED") {
    message = "The Posture Tool is not enabled for this clinic. Ask your clinic admin to enable it."
  } else if (response.status === 403 && message?.includes("posture.create")) {
    message =
      "Your account is not allowed to run posture analyses. Ask your clinic admin to grant \"Run Posture Analysis\" in Permissions."
  }

  return new ApiError(
    message || fallback || friendlyStatus(response.status),
    response.status,
    code,
    workspaces,
  )
}

function networkError(): ApiError {
  return new ApiError(
    "Could not reach the server. Check your internet connection and try again.",
    0,
    "NETWORK",
  )
}

// ------------------------------------------------------------------ re-login
// A session can end in the middle of an assessment (photos taken, points
// reviewed). Sending the clinician to the login page would throw that work
// away, so the page registers a handler that asks for the password in a
// dialog and resolves once a new token is stored. The request is then sent
// once more. Without a handler (or if the clinician cancels) the error stands.

type ReauthHandler = () => Promise<boolean>
let reauthHandler: ReauthHandler | null = null
let reauthInFlight: Promise<boolean> | null = null

export function setReauthHandler(handler: ReauthHandler | null) {
  reauthHandler = handler
}

function reauthenticate(): Promise<boolean> {
  if (!reauthHandler) return Promise.resolve(false)
  if (!reauthInFlight) {
    reauthInFlight = reauthHandler().finally(() => {
      reauthInFlight = null
    })
  }
  return reauthInFlight
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)
  try {
    return await fetch(`${API}${path}`, { ...init, headers })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err
    throw networkError()
  }
}

/** Authenticated request. One retry after a successful re-login on 401. */
async function request(path: string, init: RequestInit, fallback: string): Promise<Response> {
  let response = await send(path, init)
  if (response.status === 401 && (await reauthenticate())) {
    response = await send(path, init)
  }
  if (response.ok) return response
  throw await toApiError(response, fallback)
}

// ------------------------------------------------------------------ auth

export async function login(email: string, password: string, clinicId?: string): Promise<string> {
  let response: Response
  try {
    response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clinicId ? { email, password, clinic_id: clinicId } : { email, password }),
    })
  } catch {
    throw networkError()
  }
  if (!response.ok) {
    const error = await toApiError(response)
    if (response.status === 401) error.message = "Incorrect email or password."
    throw error
  }
  const body = await response.json()
  const token = body?.data?.access_token
  if (typeof token !== "string" || !token) {
    throw new ApiError("The server did not return a session. Please try again.", response.status)
  }
  return token
}

export interface Me {
  user: { first_name?: string | null; last_name?: string | null; email: string; role?: string }
  clinic: { id: string; name: string } | null
  capabilities?: Record<string, string>
}

/** No re-login dialog here: the gate that calls this sends a 401 to /login. */
export async function fetchMe(): Promise<Me> {
  const response = await send("/auth/me", {})
  if (!response.ok) throw await toApiError(response)
  const body = await response.json()
  return body.data as Me
}

// ------------------------------------------------------------------ posture

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

  const response = await request(
    "/posture/detect",
    { method: "POST", body: formData },
    "Landmark detection failed",
  )
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
  // Phone tilt at capture (lib/tilt.ts); null for uploads and for devices
  // that could not report it.
  frontLevel: CaptureLevel | null
  sideLevel: CaptureLevel | null
  backLevel: CaptureLevel | null
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

  const levels = { front: payload.frontLevel, side: payload.sideLevel, back: payload.backLevel }
  for (const [name, level] of Object.entries(levels)) {
    if (level) {
      formData.append(`${name}_level_deg`, String(level.degrees))
      formData.append(`${name}_level_calibrated`, level.calibrated ? "true" : "false")
    }
  }

  const response = await request(
    "/posture/report",
    { method: "POST", body: formData },
    "Report generation failed",
  )
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
export async function downloadPostureReportPdf(report: PostureReport): Promise<void> {
  const response = await request(
    "/posture/report/pdf",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    },
    "Failed to generate report PDF",
  )

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
