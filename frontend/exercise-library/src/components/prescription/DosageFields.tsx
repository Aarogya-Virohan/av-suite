import React, { useState } from "react";
import { PrescriptionItem } from "@/types/exercise";

interface DosageFieldsProps {
  item: PrescriptionItem;
  onChange: (updatedItem: PrescriptionItem) => void;
}

/*
 * "Daily" is the backend's and the library's default, so it has to be an
 * option; before, the select had no "Daily" and showed blank for every new
 * row. A saved value outside the list (older data) is kept and shown.
 */
const FREQUENCIES = ["Daily", "Twice daily", "3 times daily", "Every other day", "As needed", "Once daily"];

const fieldBase =
  "h-10 w-full rounded-[10px] border border-line bg-card px-2.5 text-sm font-semibold text-ink transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15";

/**
 * Number input that lets the user clear and retype. The old one clamped on
 * every keystroke, so clearing "10" to type "15" produced "115" or "1".
 * The value is clamped when the field loses focus.
 */
function NumberField({
  label,
  value,
  min,
  max,
  suffix,
  onCommit,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  onCommit: (v: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  const [shown, setShown] = useState(value);
  // Follow outside changes (arrow keys, a loaded prescription) without an effect.
  if (value !== shown) {
    setShown(value);
    setDraft(String(value));
  }

  const commit = () => {
    const parsed = parseInt(draft, 10);
    const next = Number.isNaN(parsed) ? value : Math.min(Math.max(parsed, min), max);
    setDraft(String(next));
    if (next !== value) onCommit(next);
  };

  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="relative block">
        <input
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          aria-label={label}
          value={draft}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, "").slice(0, 3);
            setDraft(v);
            const n = parseInt(v, 10);
            if (!Number.isNaN(n) && n >= min && n <= max) onCommit(n);
          }}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            if (e.key === "ArrowUp" || e.key === "ArrowDown") {
              e.preventDefault();
              const next = Math.min(Math.max(value + (e.key === "ArrowUp" ? 1 : -1), min), max);
              onCommit(next);
            }
          }}
          className={`${fieldBase} ${suffix ? "pr-6" : ""}`}
        />
        {suffix && (
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
            {suffix}
          </span>
        )}
      </span>
    </label>
  );
}

export function DosageFields({ item, onChange }: DosageFieldsProps) {
  const update = (patch: Partial<PrescriptionItem>) => onChange({ ...item, ...patch });
  const options = FREQUENCIES.includes(item.frequency) ? FREQUENCIES : [item.frequency, ...FREQUENCIES];

  return (
    <div className="mt-3 space-y-3">
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-[1fr_1fr_1fr_1.7fr]">
        <NumberField label="Sets" value={item.sets} min={1} max={20} onCommit={(v) => update({ sets: v })} />
        <NumberField label="Reps" value={item.reps} min={1} max={200} onCommit={(v) => update({ reps: v })} />
        <NumberField label="Hold" value={item.hold} min={0} max={600} suffix="s" onCommit={(v) => update({ hold: v })} />
        <label className="col-span-3 block sm:col-span-1">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Frequency
          </span>
          <select
            value={item.frequency}
            onChange={(e) => update({ frequency: e.target.value })}
            className={`${fieldBase} cursor-pointer appearance-none bg-[url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235d6380' stroke-width='2.5'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")] bg-[length:12px] bg-[right_10px_center] bg-no-repeat pr-8`}
          >
            {options.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
      </div>
      <input
        type="text"
        aria-label="Note for the patient"
        placeholder="Note for the patient (optional), e.g. stop if pain increases"
        value={item.note || ""}
        maxLength={500}
        onChange={(e) => update({ note: e.target.value })}
        className="h-10 w-full rounded-[10px] border border-line bg-canvas/60 px-3 text-[13px] text-ink placeholder:text-[#8a8fa6] transition-colors focus:border-grove focus:bg-card focus:outline-none focus:ring-2 focus:ring-grove/15"
      />
    </div>
  );
}
