import type { ReactNode } from "react"

// Section heading used across the report, matching the PDF: charcoal title
// with the brand teal bar, optional detail on the right, hairline below.
export default function SectionTitle({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-[#D9E3E4] pb-2.5 sm:flex-row sm:items-end sm:justify-between">
      <h2 className="border-l-[3px] border-[#4E888F] pl-2.5 text-[19px] font-bold leading-tight tracking-tight text-[#2F3336]">
        {title}
      </h2>
      {aside && <div className="flex flex-wrap items-center gap-2 sm:justify-end">{aside}</div>}
    </div>
  )
}
