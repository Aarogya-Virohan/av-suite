interface Props {
  score: number | null
  descriptor: string
  graded?: number
  attempted?: number
}

export default function GlobalIndex({
  score,
  descriptor,
  graded,
  attempted
}: Props) {
  // The index has been computable from a different number of parameters
  // for every patient, so the same severe findings can produce very
  // different scores depending on how much else was measurable. Shown
  // only when there is something to qualify.
  const basisText =
    attempted != null && attempted > 0
      ? `Based on ${graded ?? 0} of ${attempted} parameters`
      : null
  return (
    <div className="print-section print-tight rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

      <p className="text-sm uppercase tracking-wide text-slate-500">
        Global Stability Index
      </p>

      <div className="mt-6 flex flex-col items-center justify-center">

        <div
          className="
            flex
            h-44
            w-44
            items-center
            justify-center
            rounded-full
            border-8
            border-slate-900
          "
        >
          {/* A null score means nothing was graded. Rendering it would
              have printed "null%" inside the dial. */}
          <span
            className={
              score === null
                ? 'px-4 text-center text-base font-semibold text-slate-500'
                : 'text-5xl font-bold text-slate-900'
            }
          >
            {score === null ? 'Not available' : `${score}%`}
          </span>
        </div>

        <p className="mt-6 text-xl font-semibold text-slate-900">
          {descriptor}
        </p>

        {basisText && (
          <p className="mt-2 text-sm text-slate-500">
            {basisText}
          </p>
        )}

      </div>
    </div>
  )
}