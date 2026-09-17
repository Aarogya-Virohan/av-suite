interface Props {
  score: number | null
  descriptor: string
}

export default function GlobalIndex({
  score,
  descriptor
}: Props) {
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

      </div>
    </div>
  )
}