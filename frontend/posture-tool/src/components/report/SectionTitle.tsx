import type { ReactNode } from "react"

// Section heading used across the report, matching the PDF since
// 13 October 2026: a Grove dot and a Midnight title, optional detail on the
// right.
export default function SectionTitle({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <h2 className="flex items-center gap-2.5 font-display text-[19px] font-bold leading-tight tracking-tight text-[#0B1238]">
        <span aria-hidden="true" className="h-2 w-2 flex-none rounded-full bg-[#1C7A54]" />
        {title}
      </h2>
      {aside && <div className="flex flex-wrap items-center gap-2 sm:justify-end">{aside}</div>}
    </div>
  )
}
