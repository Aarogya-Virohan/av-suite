import React from "react";
import { cn } from "@/lib/utils";

interface FilterChipsProps {
  parts: string[];
  selectedParts: string[];
  onToggle: (part: string) => void;
  onClear: () => void;
}

/**
 * Body part filter. A click filters straight away (no Apply button);
 * several parts can be on at once, "All" clears them.
 */
export function FilterChips({ parts, selectedParts, onToggle, onClear }: FilterChipsProps) {
  const chip = (active: boolean) =>
    cn(
      "h-8 shrink-0 cursor-pointer rounded-full border px-3.5 text-[13px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25",
      active
        ? "border-midnight bg-midnight text-white"
        : "border-line bg-card text-ink-2 hover:border-grove/40 hover:text-ink"
    );

  return (
    <div
      role="group"
      aria-label="Filter by body part"
      className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0"
    >
      <button type="button" aria-pressed={selectedParts.length === 0} className={chip(selectedParts.length === 0)} onClick={onClear}>
        All
      </button>
      {parts.map((part) => {
        const active = selectedParts.includes(part);
        return (
          <button key={part} type="button" aria-pressed={active} className={chip(active)} onClick={() => onToggle(part)}>
            {part}
          </button>
        );
      })}
    </div>
  );
}
