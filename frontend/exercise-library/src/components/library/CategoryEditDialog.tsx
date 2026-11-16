"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, X } from "lucide-react";
import { ApiError, updateExerciseCategories, type CategoryGroup } from "@/lib/api";
import { GroupBox } from "@/components/library/CategoryFilter";
import { toast } from "@/components/ui/toaster";
import { displayTitle } from "@/lib/displayTitle";
import type { Exercise } from "@/types/exercise";

interface CategoryEditDialogProps {
  exercise: Exercise;
  groups: CategoryGroup[];
  onClose: () => void;
  onSaved: (exercise: Exercise) => void;
}

/**
 * Set the categories of one of the clinic's own exercises (EL-L-10).
 * Global exercises are part of the AV library and are not editable by a
 * clinic (EL-D-008), so the card never opens this for them.
 */
export function CategoryEditDialog({ exercise, groups, onClose, onSaved }: CategoryEditDialogProps) {
  const [selected, setSelected] = useState<string[]>(exercise.categoryIds ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCloseRef.current();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const initial = useMemo(() => [...(exercise.categoryIds ?? [])].sort().join(","), [exercise.categoryIds]);
  const changed = [...selected].sort().join(",") !== initial;

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateExerciseCategories(exercise.id, selected);
      onSaved(updated);
      toast("Categories saved");
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="category-dialog-title"
        className="flex max-h-[92vh] w-full max-w-lg flex-col rounded-t-2xl border border-line bg-canvas shadow-card sm:rounded-2xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line bg-card p-4 sm:rounded-t-2xl">
          <div className="min-w-0">
            <h2 id="category-dialog-title" className="font-display text-base font-bold text-ink">
              {displayTitle(exercise.name)}
            </h2>
            <p className="mt-0.5 text-xs text-ink-2">Categories used by the filters. {selected.length} selected.</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
            className="grid h-9 w-9 shrink-0 cursor-pointer place-items-center rounded-[10px] text-ink-2 hover:bg-grove-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-3">
          {groups.map((g) => (
            <GroupBox key={g.key} group={g} selected={selected} onToggle={toggle} />
          ))}
          {groups.length === 0 && <p className="p-2 text-sm text-ink-2">Categories could not be loaded.</p>}
        </div>

        <div className="border-t border-line bg-card p-3 sm:rounded-b-2xl">
          {error && (
            <p role="alert" className="mb-2 text-xs font-medium text-danger">
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="h-10 flex-1 cursor-pointer rounded-[10px] border border-line text-sm font-semibold text-ink-2 hover:bg-grove-wash"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving || !changed || groups.length === 0}
              className="flex h-10 flex-1 cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-grove text-sm font-semibold text-white shadow-primary hover:bg-grove-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save categories
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
