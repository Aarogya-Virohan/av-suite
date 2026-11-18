"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, UserPlus, X } from "lucide-react";
import { Patient } from "@/types/exercise";
import { cn } from "@/lib/utils";

interface PatientPickerProps {
  patients: Patient[];
  value: string;
  onChange: (id: string) => void;
  onAddNew: () => void;
  loading: boolean;
}

export function patientLabel(p: Patient): string {
  return `${p.first_name} ${p.last_name}`.trim();
}

/**
 * Searchable patient picker: type part of a name or phone, arrow keys and
 * Enter to pick. Replaces the plain dropdown, which meant scrolling through
 * every patient of the clinic.
 */
export function PatientPicker({ patients, value, onChange, onAddNew, loading }: PatientPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = patients.find((p) => p.id === value);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return patients;
    const digits = q.replace(/\D/g, "");
    return patients.filter(
      (p) =>
        patientLabel(p).toLowerCase().includes(q) || (digits.length > 0 && (p.phone ?? "").includes(digits))
    );
  }, [patients, query]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const choose = (p: Patient) => {
    onChange(p.id);
    setOpen(false);
    setQuery("");
  };

  const openPicker = () => {
    setOpen(true);
    setActive(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  return (
    <div ref={rootRef} className="relative">
      {!open ? (
        <button
          type="button"
          onClick={openPicker}
          aria-haspopup="listbox"
          className={cn(
            "flex h-11 w-full cursor-pointer items-center gap-2 rounded-[10px] border bg-card px-3 text-left text-sm transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15",
            selected ? "border-line" : "border-dashed border-grove/40"
          )}
        >
          {selected ? (
            <>
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-grove-wash text-[11px] font-bold text-grove">
                {selected.first_name[0]}
                {selected.last_name?.[0]}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold text-ink">{patientLabel(selected)}</span>
              </span>
              {selected.phone && <span className="text-xs text-muted-foreground">{selected.phone}</span>}
            </>
          ) : (
            <span className="flex-1 text-muted-foreground">{loading ? "Loading patients..." : "Choose a patient"}</span>
          )}
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        </button>
      ) : (
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767b93]" />
          <input
            ref={inputRef}
            role="combobox"
            aria-expanded
            aria-controls="patient-options"
            aria-activedescendant={matches[active] ? `patient-${matches[active].id}` : undefined}
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
                if (matches[active]) choose(matches[active]);
              } else if (e.key === "Escape") {
                setOpen(false);
              }
            }}
            placeholder="Search by name or phone"
            className="h-11 w-full rounded-[10px] border border-grove bg-card pl-10 pr-10 text-sm text-ink outline-none ring-2 ring-grove/15"
          />
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close"
            className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 cursor-pointer place-items-center rounded-md text-muted-foreground hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {open && (
        <div className="absolute inset-x-0 top-[calc(100%+6px)] z-30 overflow-hidden rounded-xl border border-line bg-card shadow-[0_18px_40px_-18px_rgba(11,18,56,0.35)]">
          <ul id="patient-options" role="listbox" className="max-h-64 overflow-y-auto py-1">
            {matches.map((p, i) => (
              <li
                key={p.id}
                id={`patient-${p.id}`}
                role="option"
                aria-selected={p.id === value}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(p);
                }}
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-3 px-3 py-2.5 text-sm",
                  i === active ? "bg-grove-wash" : "",
                  p.id === value ? "font-semibold text-grove" : "text-ink"
                )}
              >
                <span className="truncate">{patientLabel(p)}</span>
                {p.phone && <span className="shrink-0 text-xs text-muted-foreground">{p.phone}</span>}
              </li>
            ))}
            {matches.length === 0 && (
              <li className="px-3 py-3 text-sm text-muted-foreground">
                {patients.length === 0 ? "No patients yet." : "No patient matches."}
              </li>
            )}
          </ul>
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault();
              setOpen(false);
              onAddNew();
            }}
            className="flex w-full cursor-pointer items-center gap-2 border-t border-line px-3 py-2.5 text-sm font-semibold text-grove hover:bg-grove-wash"
          >
            <UserPlus className="h-4 w-4" />
            Add new patient
          </button>
        </div>
      )}
    </div>
  );
}
