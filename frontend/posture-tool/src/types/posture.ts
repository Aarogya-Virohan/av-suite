export type Severity =
  | "none"
  | "mild"
  | "moderate"
  | "severe"
  | "insufficient_data"

export interface Measurement {
  label: string
  value: number | string
  unit: string
  severityLabel: string
  severity: Severity
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
    score: number
    descriptor: string
  }
}