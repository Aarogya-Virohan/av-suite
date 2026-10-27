"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search, SlidersHorizontal, X } from "lucide-react";
import type { CategoryGroup } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CategoryFilterProps {
  groups: CategoryGroup[];
  selected: string[];
  onChange: (next: string[]) => void;
  total: number;
  unavailable?: boolean;
}

const PREVIEW = 6;

/**
 * Category filter (EL-D-005). A "Filters" button opens a panel with every
 * category group (Joint/Region, Position, Equipment and so on), each value
 * with how many exercises carry it. Ticks apply straight away. Inside one
 * group any ticked value matches; across groups every group must match.
 * Ticked values stay visible under the search as removable pills.
 */
export function CategoryFilter({ groups, selected, onChange, total, unavailable }: CategoryFilterProps) {
  const [open, setOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  const byId = useMemo(() => {
    const map = new Map<string, { name: string; group: string }>();
    for (const g of groups) for (const v of g.values) map.set(v.id, { name: v.name, group: g.label });
    return map;
  }, [groups]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    const t = requestAnimationFrame(() => closeRef.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      cancelAnimationFrame(t);
    };
  }, [open]);

  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={unavailable}
        aria-haspopup="dialog"
        className="flex h-11 w-full cursor-pointer items-center gap-2 rounded-[10px] border border-line bg-card px-3 text-left text-sm transition-colors hover:border-grove focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <SlidersHorizontal className="h-4 w-4 shrink-0 text-grove" />
        <span className="flex-1 font-semibold text-ink">{unavailable ? "Filters not available" : "Filters"}</span>
        {selected.length > 0 && (
          <span className="grid h-5 min-w-5 place-items-center rounded-full bg-grove px-1.5 text-[11px] font-bold text-white">
            {selected.length}
          </span>
        )}
      </button>

      {selected.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5" aria-label="Selected filters">
          {selected.map((id) => {
            const item = byId.get(id);
            if (!item) return null;
            return (
              <span
                key={id}
                title={item.group}
                className="inline-flex h-7 items-center gap-1 rounded-full bg-midnight pl-3 pr-1 text-xs font-semibold text-white"
              >
                {item.name}
                <button
                  type="button"
                  onClick={() => toggle(id)}
                  aria-label={`Remove ${item.name}`}
                  className="grid h-5 w-5 cursor-pointer place-items-center rounded-full hover:bg-white/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            );
          })}
          <button
            type="button"
            onClick={() => onChange([])}
            className="cursor-pointer px-1 text-xs font-semibold text-grove hover:text-grove-hover"
          >
            Clear all
          </button>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Filters">
          <button
            type="button"
            aria-label="Close filters"
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="absolute inset-0 cursor-default bg-midnight/40"
          />
          <div className="relative flex h-full w-full max-w-[400px] flex-col bg-canvas shadow-[0_18px_40px_-18px_rgba(11,18,56,0.45)]">
            <div className="flex items-center gap-2 border-b border-line bg-card px-4 py-3">
              <SlidersHorizontal className="h-4 w-4 text-grove" />
              <h2 className="flex-1 font-display text-base font-bold text-ink">Filters</h2>
              <button
                type="button"
                disabled={selected.length === 0}
                onClick={() => onChange([])}
                className="cursor-pointer text-xs font-semibold text-grove hover:text-grove-hover disabled:cursor-default disabled:text-muted-foreground"
              >
                Clear
              </button>
              <button
                ref={closeRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-ink-2 hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-3">
              {groups.map((g) => (
                <GroupBox key={g.key} group={g} selected={selected} onToggle={toggle} />
              ))}
            </div>
            <div className="border-t border-line bg-card p-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="h-10 w-full cursor-pointer rounded-[10px] bg-grove text-sm font-semibold text-white shadow-primary hover:bg-grove-hover"
              >
                Show {total} {total === 1 ? "exercise" : "exercises"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GroupBox({
  group,
  selected,
  onToggle,
}: {
  group: CategoryGroup;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState("");
  const searchable = group.values.length > PREVIEW;
  const picked = group.values.filter((v) => selected.includes(v.id)).length;

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q) return group.values.filter((v) => v.name.toLowerCase().includes(q));
    return expanded ? group.values : group.values.slice(0, PREVIEW);
  }, [group.values, query, expanded]);

  return (
    <section className="rounded-xl border border-line bg-card p-3" aria-label={group.label}>
      <h3 className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {group.label}
        {picked > 0 && <span className="normal-case tracking-normal text-grove">{picked} selected</span>}
      </h3>
      {searchable && (
        <div className="relative mb-1.5">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#767b93]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={`Search ${group.label}`}
            placeholder={`Search ${group.label.toLowerCase()}`}
            className="h-8 w-full rounded-lg border border-line bg-canvas/60 pl-8 pr-2 text-sm text-ink placeholder:text-[#8a8fa6] focus:border-grove focus:bg-card focus:outline-none"
          />
        </div>
      )}
      <ul className="space-y-0.5">
        {shown.map((v) => {
          const on = selected.includes(v.id);
          return (
            <li key={v.id}>
              <label className="flex cursor-pointer items-center gap-2.5 rounded-md px-1.5 py-1.5 text-sm hover:bg-grove-wash">
                <input type="checkbox" checked={on} onChange={() => onToggle(v.id)} className="peer sr-only" />
                <span
                  aria-hidden
                  className={cn(
                    "grid h-4 w-4 shrink-0 place-items-center rounded border peer-focus-visible:ring-2 peer-focus-visible:ring-grove/30",
                    on ? "border-grove bg-grove text-white" : "border-[#c9c2b2] bg-card"
                  )}
                >
                  {on && <Check className="h-3 w-3" strokeWidth={3} />}
                </span>
                <span className={cn("flex-1", on ? "font-semibold text-ink" : v.count ? "text-ink-2" : "text-muted-foreground")}>
                  {v.name}
                </span>
                <span className="text-xs tabular-nums text-muted-foreground">{v.count}</span>
              </label>
            </li>
          );
        })}
        {shown.length === 0 && <li className="px-1.5 py-2 text-sm text-muted-foreground">No match.</li>}
      </ul>
      {!query && group.values.length > PREVIEW && (
        <button
          type="button"
          onClick={() => setExpanded((x) => !x)}
          aria-expanded={expanded}
          className="mt-1 flex cursor-pointer items-center gap-1 px-1.5 text-xs font-semibold text-grove hover:text-grove-hover"
        >
          {expanded ? "Show less" : `Show all ${group.values.length}`}
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
        </button>
      )}
    </section>
  );
}
