export type Severity =
  | "none"
  | "mild"
  | "moderate"
  | "severe"
  | "insufficient_data"
  | "not_available"

export interface Measurement {
  paramId: string
  label: string
  value: number | string | null
  unit: string
  severityLabel: string
  severity: Severity
  borderline: boolean

  // Which way the deviation goes, from the patient's own perspective, with
  // sideLabel carrying the wording to print. Both come from the backend so
  // the phrase is identical here and on the PDF.
  //
  // sideLabel is sent whenever a direction exists, including at severities
  // this view does not show it at. Deciding when to show it is this
  // component's job, not the payload's.
  side: "left" | "right" | null
  sideLabel: string | null
}

export interface ViewData {
  photoUrl: string
  accuracy: number
  measurements: Measurement[]
  interpretation: string
}

export interface SynthesisData {
  hypertonic: string[]
  inhibited: string[]

  // Removed from new reports on 11 October 2026 (founders, answer 1b).
  // Reports saved before then still carry it; nothing displays it.
  correctiveProtocol?: {
    exercise: string
    dosage: string
  }[]
}

export interface PostureReport {
  patient: {
    name: string
    age: number
    caseRef: string
    assessmentDate: string
    clinician: string
  }

  views: {
    side: ViewData
    front: ViewData
    back: ViewData
  }

  synthesis: SynthesisData

  // Which state of the analysis code produced this report. Grades move
  // when thresholds, sign conventions or calibration change, so two
  // reports for the same patient are only comparable if this matches.
  // Optional because reports generated before 18 Sept 2026 do not carry
  // it, and the absence of it is itself the signal that a report predates
  // the September threshold work.
  analysisVersion?: string

  // globalIndex removed 10 October 2026, founders' Q5. Reports saved
  // before then still carry it; nothing reads it.

  // Founders' Q5 replacement, the regional profile, since 11 October 2026.
  // Optional because earlier reports do not carry it.
  signature?: BiomechanicalSignature
}

export interface SignatureParameter {
  paramId: string
  label: string
  view: "side" | "front" | "back"
  severity: Severity
  // 0 normal to 3 severe; null when the parameter was not measured.
  tier: number | null
  value: number | string | null
  unit: string
}

export interface SignatureRegion {
  id: string
  label: string
  // Worst grade among the region's measured parameters; null when none was
  // measured or the region has no parameter (thoracic).
  worst: Severity | null
  worstLabel: string | null
  measured: number
  parameters: SignatureParameter[]
}

export interface BiomechanicalSignature {
  regions: SignatureRegion[]
  // Drawn by the server (signature_svg.py) so the web report and the PDF
  // show the same picture.
  svg?: string
}

// Landmark review step, founders' Q6, 10 October 2026.

export interface ReviewPoint {
  index: number
  name: string
  // Normalised to the photograph, 0 to 1, origin top left.
  x: number
  y: number
  visibility: number
}

export interface ReviewPupil {
  name: string
  x: number
  y: number
}

export interface DetectedViewForReview {
  widthPx: number
  heightPx: number
  // The server's decoded copy of the photograph, the one that was measured.
  displayImage: string
  points: ReviewPoint[]
  lateralSide?: "left" | "right"
  // Front view only; null when no face was found.
  iris?: ReviewPupil[] | null
}

export interface DetectionResult {
  detectionToken: string
  views: {
    side: DetectedViewForReview
    front: DetectedViewForReview
    back: DetectedViewForReview
  }
}

export interface ReviewedPoint {
  index: number
  x: number
  y: number
  notVisible?: boolean
}

export interface ReviewedView {
  points: ReviewedPoint[]
  iris?: { x: number; y: number }[] | null
  irisNotVisible?: boolean
}

export interface LandmarkReviewSubmission {
  confirmed: true
  side: ReviewedView
  front: ReviewedView
  back: ReviewedView
}
