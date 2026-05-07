export type Severity = 'None' | 'Mild' | 'Moderate' | 'Severe'

export interface Finding {
  bodyPart: string
  observation: string
  severity: Severity
}

export interface PostureAnalysis {
  patientName: string
  patientAge: number
  date: string
  overallScore: number
  findings: Finding[]
  recommendations: string[]
  therapistNotes: string
}