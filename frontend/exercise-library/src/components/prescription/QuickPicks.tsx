import React from "react";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

const norm = (s: string) => s.toLowerCase().replace(/\s+/g, " ").trim();

/** True if `text` already contains `phrase` (ignoring case and spacing). */
export function hasPhrase(text: string, phrase: string): boolean {
  return norm(text).includes(norm(phrase));
}

/**
 * Append a phrase to free text with a separator, once, within maxLength.
 * Returns the text unchanged if it is already there or would not fit.
 */
export function addPhrase(text: string, phrase: string, separator: string, maxLength: number): string {
  if (hasPhrase(text, phrase)) return text;
  const base = text.replace(/[\s,;]+$/, "");
  const next = base ? `${base}${separator}${phrase}` : phrase;
  return next.length > maxLength ? text : next;
}

interface QuickPicksProps {
  label: string;
  options: string[];
  current: string;
  onPick: (phrase: string) => void;
  singleLine?: boolean;
  max?: number;
}

/**
 * Tap-to-add phrases (founders, 23 Oct: "tap and choose, multiple options,
 * that grow over time"). Options are what this clinic already wrote, most
 * used first; one already in the text is hidden. Typing stays possible.
 */
export function QuickPicks({ label, options, current, onPick, singleLine, max = 8 }: QuickPicksProps) {
  const shown = options.filter((o) => !hasPhrase(current, o)).slice(0, max);
  if (shown.length === 0) return null;

  return (
    <div
      role="group"
      aria-label={label}
      className={cn(
        "flex gap-1.5",
        singleLine ? "-mx-0.5 overflow-x-auto px-0.5 pb-0.5 [scrollbar-width:none]" : "flex-wrap"
      )}
    >
      {shown.map((phrase) => (
        <button
          key={phrase}
          type="button"
          onClick={() => onPick(phrase)}
          title={phrase}
          className="inline-flex h-7 max-w-[240px] shrink-0 cursor-pointer items-center gap-1 rounded-full border border-line bg-card px-2.5 text-xs font-medium text-ink-2 transition-colors hover:border-grove/40 hover:bg-grove-wash hover:text-grove focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
        >
          <Plus className="h-3 w-3 shrink-0" />
          <span className="truncate">{phrase}</span>
        </button>
      ))}
    </div>
  );
}
