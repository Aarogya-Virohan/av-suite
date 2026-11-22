import React from "react";
import { X } from "lucide-react";
import { PrescriptionItem, Side } from "@/types/exercise";
import { DosageFields } from "./DosageFields";
import { displayTitle } from "@/lib/displayTitle";
import { cn } from "@/lib/utils";

interface ExerciseRowProps {
  index: number;
  item: PrescriptionItem;
  onChange: (updatedItem: PrescriptionItem) => void;
  onRemove: (id: string) => void;
  noteSuggestions: string[];
}

const SIDES: { value: Side; label: string }[] = [
  { value: "left", label: "Left" },
  { value: "right", label: "Right" },
];

export function ExerciseRow({ index, item, onChange, onRemove, noteSuggestions }: ExerciseRowProps) {
  const needsSide = !!item.exercise.requiresSide;
  const missingSide = needsSide && !item.side;
  return (
    <li className="rounded-2xl border border-line bg-card p-3.5 shadow-card">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-midnight text-[11px] font-bold text-white">
          {index}
        </span>
        <div className="min-w-0 flex-1">
          <h4 className="font-display text-[15px] font-bold leading-snug text-ink">
            {displayTitle(item.exercise.name)}
          </h4>
          <p className="text-xs font-medium text-muted-foreground">
            {item.exercise.bodyPart}
            {item.exercise.rxMode === "BLOCKED" && (
              <span className="ml-2 rounded-md bg-danger-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-danger">
                Therapist only: remove
              </span>
            )}
            {item.exercise.rxMode === "HIDDEN" && (
              <span className="ml-2 rounded-md bg-danger-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-danger">
                No longer offered: remove
              </span>
            )}
            {item.exercise.rxMode === "CAREGIVER" && (
              <span className="ml-2 rounded-md bg-info-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-info">
                Caregiver-assisted
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onRemove(item.exercise.id)}
          aria-label={`Remove ${item.exercise.name}`}
          className="grid h-8 w-8 shrink-0 cursor-pointer place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-danger-wash hover:text-danger"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {needsSide && (
        <fieldset className="mt-3">
          <legend className={cn("mb-1.5 text-[11px] font-bold uppercase tracking-wide", missingSide ? "text-danger" : "text-muted-foreground")}>
            Affected side {missingSide && "(choose before saving)"}
          </legend>
          <div className="flex gap-2" role="radiogroup" aria-label={`Affected side for ${item.exercise.name}`}>
            {SIDES.map((s) => {
              const on = item.side === s.value;
              return (
                <button
                  key={s.value}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => onChange({ ...item, side: s.value })}
                  className={cn(
                    "h-9 flex-1 cursor-pointer rounded-[10px] border text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25",
                    on ? "border-grove bg-grove text-white" : missingSide ? "border-danger/50 bg-card text-ink" : "border-line bg-card text-ink hover:border-grove/40"
                  )}
                >
                  {s.label}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}
      <DosageFields item={item} onChange={onChange} noteSuggestions={noteSuggestions} />
    </li>
  );
}
