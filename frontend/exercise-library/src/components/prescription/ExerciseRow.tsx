import React from "react";
import { X } from "lucide-react";
import { PrescriptionItem } from "@/types/exercise";
import { DosageFields } from "./DosageFields";
import { displayTitle } from "@/lib/displayTitle";

interface ExerciseRowProps {
  index: number;
  item: PrescriptionItem;
  onChange: (updatedItem: PrescriptionItem) => void;
  onRemove: (id: string) => void;
  noteSuggestions: string[];
}

export function ExerciseRow({ index, item, onChange, onRemove, noteSuggestions }: ExerciseRowProps) {
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
          <p className="text-xs font-medium text-muted-foreground">{item.exercise.bodyPart}</p>
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
      <DosageFields item={item} onChange={onChange} noteSuggestions={noteSuggestions} />
    </li>
  );
}
