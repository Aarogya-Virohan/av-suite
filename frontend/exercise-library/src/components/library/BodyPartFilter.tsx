"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import type { BodyPartCount } from "@/lib/api";
import { cn } from "@/lib/utils";

interface BodyPartFilterProps {
  parts: BodyPartCount[];
  selected: string[];
  onChange: (next: string[]) => void;
  unavailable?: boolean;
}

/**
 * Body part filter as a dropdown (founders, 23 Oct: chips will not scale to
 * 30+ categories). Options come from the backend already in head-to-toe
 * order, with counts. Several parts can be picked; each tick filters straight
 * away, as the chips did. Picked parts stay visible as removable pills.
 */
export function BodyPartFilter({ parts, selected, onChange, unavailable }: BodyPartFilterProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? parts.filter((p) => p.body_part.toLowerCase().includes(q)) : parts;
  }, [parts, query]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const toggle = (name: string) =>
    onChange(selected.includes(name) ? selected.filter((s) => s !== name) : [...selected, name]);

  const openMenu = () => {
    setOpen(true);
    setQuery("");
    setActive(0);
    requestAnimationFrame(() => searchRef.current?.focus());
  };

  const label =
    selected.length === 0
      ? "All body parts"
      : selected.length === 1
        ? selected[0]
        : `${selected.length} body parts`;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => (open ? setOpen(false) : openMenu())}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={unavailable}
        className={cn(
          "flex h-11 w-full cursor-pointer items-center gap-2 rounded-[10px] border bg-card px-3 text-left text-sm transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 disabled:cursor-not-allowed disabled:opacity-60",
          open ? "border-grove" : "border-line"
        )}
      >
        <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Body part</span>
        <span className={cn("min-w-0 flex-1 truncate font-semibold", selected.length ? "text-ink" : "text-ink-2")}>
          {unavailable ? "Not available" : label}
        </span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute inset-x-0 top-[calc(100%+6px)] z-30 overflow-hidden rounded-xl border border-line bg-card shadow-[0_18px_40px_-18px_rgba(11,18,56,0.35)]">
          <div className="relative border-b border-line p-2">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767b93]" />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
              }}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setActive((a) => Math.min(a + 1, matches.length - 1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setActive((a) => Math.max(a - 1, 0));
                } else if (e.key === "Enter") {
                  e.preventDefault();
                  if (matches[active]) toggle(matches[active].body_part);
                } else if (e.key === "Escape") {
                  setOpen(false);
                }
              }}
              aria-label="Search body parts"
              aria-controls="body-part-options"
              placeholder="Search body parts"
              className="h-9 w-full rounded-lg border border-line bg-canvas/60 pl-8 pr-3 text-sm text-ink placeholder:text-[#8a8fa6] focus:border-grove focus:bg-card focus:outline-none"
            />
          </div>
          <ul id="body-part-options" role="listbox" aria-multiselectable className="max-h-72 overflow-y-auto py-1">
            {matches.map((p, i) => {
              const on = selected.includes(p.body_part);
              return (
                <li
                  key={p.body_part}
                  role="option"
                  aria-selected={on}
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    toggle(p.body_part);
                  }}
                  className={cn(
                    "flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm",
                    i === active && "bg-grove-wash"
                  )}
                >
                  <span
                    className={cn(
                      "grid h-4 w-4 shrink-0 place-items-center rounded border",
                      on ? "border-grove bg-grove text-white" : "border-[#c9c2b2] bg-card"
                    )}
                  >
                    {on && <Check className="h-3 w-3" strokeWidth={3} />}
                  </span>
                  <span className={cn("flex-1", on ? "font-semibold text-ink" : "text-ink-2")}>{p.body_part}</span>
                  <span className="text-xs tabular-nums text-muted-foreground">{p.count}</span>
                </li>
              );
            })}
            {matches.length === 0 && <li className="px-3 py-3 text-sm text-muted-foreground">No body part matches.</li>}
          </ul>
          <div className="flex items-center justify-between border-t border-line px-3 py-2">
            <button
              type="button"
              disabled={selected.length === 0}
              onClick={() => onChange([])}
              className="cursor-pointer text-xs font-semibold text-grove hover:text-grove-hover disabled:cursor-default disabled:text-muted-foreground"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="h-8 cursor-pointer rounded-lg bg-grove px-3 text-xs font-semibold text-white hover:bg-grove-hover"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {selected.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Selected body parts">
          {selected.map((name) => (
            <span
              key={name}
              className="inline-flex h-7 items-center gap-1 rounded-full bg-midnight pl-3 pr-1 text-xs font-semibold text-white"
            >
              {name}
              <button
                type="button"
                onClick={() => toggle(name)}
                aria-label={`Remove ${name}`}
                className="grid h-5 w-5 cursor-pointer place-items-center rounded-full hover:bg-white/20"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
