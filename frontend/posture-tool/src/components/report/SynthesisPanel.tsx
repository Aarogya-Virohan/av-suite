import { SynthesisData } from "@/types/posture"
import SectionTitle from "./SectionTitle"

interface Props {
  data: SynthesisData
}

// Headings say "Likely", as the PDF always has. The web said plain
// "Hypertonic" / "Inhibited" until 11 October 2026, which states as fact
// what a 2D photograph can only suggest.
function MuscleList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#1C7A54]">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-[14px] italic text-[#5D6380]">None identified</p>
      ) : (
        <ul className="mt-2 space-y-1 text-[14px] text-[#141A33]">
          {items.map((muscle) => (
            <li key={muscle} className="flex gap-2">
              <span className="text-[#1C7A54]">&bull;</span>
              {muscle}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function SynthesisPanel({ data }: Props) {
  return (
    <section className="print-section">
      <SectionTitle title="Clinical Synthesis" />

      {/* No exercises since 11 October 2026: the founders removed them from
          the automated report (answer 1b). The physiotherapist prescribes. */}
      <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <MuscleList title="Likely hypertonic" items={data.hypertonic} />
        <MuscleList title="Likely inhibited" items={data.inhibited} />
      </div>
    </section>
  )
}
