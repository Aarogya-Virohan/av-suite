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

  correctiveProtocol: {
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

  globalIndex: {
    // Null when no parameter produced a grade. The backend used to send 100
    // with "Optimal Alignment" in that case; it now sends null and
    // "Not assessable", so this must stay nullable.
    score: number | null
    descriptor: string
    // How many parameters the score rests on, and how many rows the report
    // printed. Carried for now, not rendered: how an incomplete index should
    // be shown is an open clinical question.
    graded?: number
    attempted?: number
  }
}