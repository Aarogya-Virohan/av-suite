"use client"

import { useEffect, useState } from "react"

import { searchPatients, type PickerPatient } from "@/lib/api"

// Pick one of the clinic's CRM patients (POS-2). There is no way to type a new
// patient here: a patient is created in the CRM and then found by name or by
// the CRM patient ID.

const INPUT_CLASS =
  "h-11 w-full rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[15px] text-[#141A33] outline-none transition placeholder:text-[#8B90A8] focus:border-[#4E888F]"

export function ageSex(p: PickerPatient): string {
  return [p.age != null ? `${p.age} Y` : "Age not in CRM", p.gender].filter(Boolean).join(" / ")
}

export default function PatientPicker({
  onSelect,
  error,
}: {
  onSelect: (patient: PickerPatient) => void
  error?: string | null
}) {
  const [term, setTerm] = useState("")
  const [results, setResults] = useState<PickerPatient[] | null>(null)
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(
      async () => {
        try {
          const found = await searchPatients(term.trim(), controller.signal)
          setResults(found)
          setFailed(null)
        } catch (e) {
          if (e instanceof DOMException && e.name === "AbortError") return
          setFailed(e instanceof Error ? e.message : "Could not load patients")
        }
      },
      term === "" ? 0 : 250,
    )
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [term])

  return (
    <div>
      <label className="block">
        <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">
          Find a patient
          <span className="ml-0.5 text-[#B4231B]" aria-hidden="true">
            *
          </span>
        </span>
        <input
          type="search"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Name or patient ID, for example SPC-000123"
          className={INPUT_CLASS}
          autoComplete="off"
          data-testid="patient-search"
        />
      </label>
      {error && (
        <p role="alert" className="mt-1 text-[12px] font-medium text-[#B4231B]">
          {error}
        </p>
      )}

      <div className="mt-2 overflow-hidden rounded-xl border border-[#E3DCCB] bg-[#FFFDF7]" data-testid="patient-results">
        {failed ? (
          <p role="alert" className="px-3 py-3 text-[13px] text-[#8C1D18]">
            {failed}
          </p>
        ) : results === null ? (
          <p className="px-3 py-3 text-[13px] text-[#5D6380]">Loading patients...</p>
        ) : results.length === 0 ? (
          <p className="px-3 py-3 text-[13px] text-[#5D6380]">
            No patient found. Patients are added in the CRM; add the patient there, then search again.
          </p>
        ) : (
          <ul className="max-h-72 divide-y divide-[#EFE8D6] overflow-y-auto">
            {results.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onSelect(p)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-[#F3EEE2]"
                  data-testid="patient-option"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-medium text-[#141A33]">{p.name}</span>
                    <span className="block text-[12.5px] text-[#5D6380]">{ageSex(p)}</span>
                  </span>
                  <span className="flex-none font-mono text-[12px] font-semibold text-[#454B66]">{p.caseId}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
