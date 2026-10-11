import type { Severity } from "@/types/posture"
import { getSeverityColor } from "@/lib/getSeverityColor"

// One badge for every grade on the report, so a "Mild deviation" looks the
// same in a view table and in the signature list. Same colours as the PDF.
export default function SeverityBadge({ severity, label }: { severity: Severity; label: string }) {
  const c = getSeverityColor(severity)
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase tracking-[0.04em] ${c.badgeBg} ${c.badgeText} ${c.badgeBorder}`}
    >
      {label}
    </span>
  )
}
