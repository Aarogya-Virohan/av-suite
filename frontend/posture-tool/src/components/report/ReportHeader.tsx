interface ReportHeaderProps {
  patient: {
    name: string
    age: number
    caseRef: string
    assessmentDate: string
    clinician: string
  }
}

export default function ReportHeader({
  patient
}: ReportHeaderProps) {
  return (
    <div className="bg-white border rounded-2xl p-6 shadow-sm">

      {/* Top Row */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

        {/* Left */}
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-500">
            Clinical Posture Assessment
          </p>

          <h1 className="text-3xl font-bold text-slate-900 mt-1">
            {patient.name}
          </h1>

          <p className="text-slate-600 mt-1">
            Age {patient.age}
          </p>
        </div>

        {/* Right */}
        <div className="grid grid-cols-1 gap-3 text-sm">

          <div>
            <p className="text-slate-500">
              Case Reference
            </p>

            <p className="font-medium text-slate-900">
              {patient.caseRef}
            </p>
          </div>

          <div>
            <p className="text-slate-500">
              Assessment Date
            </p>

            <p className="font-medium text-slate-900">
              {patient.assessmentDate}
            </p>
          </div>

          <div>
            <p className="text-slate-500">
              Lead Clinician
            </p>

            <p className="font-medium text-slate-900">
              {patient.clinician}
            </p>
          </div>

        </div>
      </div>
    </div>
  )
}