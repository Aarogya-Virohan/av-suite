"use client";

import React, { useCallback, useEffect, useState } from "react";
import { BookmarkPlus, LayoutTemplate, Loader2, Trash2 } from "lucide-react";
import { PrescriptionItem } from "@/types/exercise";
import {
  createTemplate,
  deleteTemplate,
  fetchTemplates,
  mapBackendExerciseToFrontend,
  type ExerciseTemplate,
} from "@/lib/api";
import { toast } from "@/components/ui/toaster";

const NAME_MAX = 200;
const DESCRIPTION_MAX = 2000;

interface TemplatesPanelProps {
  /** Exercises on screen, offered for "Save as template". */
  current: PrescriptionItem[];
  /** Fill the prescription with a template's exercises (EL-D-009). */
  onUse: (items: PrescriptionItem[], name: string) => void;
}

/** A template's rows as prescription items; exercises no longer in the
 * library are left out and counted. */
function toItems(t: ExerciseTemplate): { items: PrescriptionItem[]; missing: number } {
  const items: PrescriptionItem[] = [];
  let missing = 0;
  for (const it of t.items) {
    if (!it.exercise) {
      missing++;
      continue;
    }
    items.push({
      exercise: mapBackendExerciseToFrontend(it.exercise),
      sets: it.sets,
      reps: it.reps,
      hold: it.hold,
      frequency: it.frequency,
      note: it.note ?? undefined,
    });
  }
  return { items, missing };
}

export function TemplatesPanel({ current, onUse }: TemplatesPanelProps) {
  const [templates, setTemplates] = useState<ExerciseTemplate[] | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showSave, setShowSave] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const use = (t: ExerciseTemplate) => {
    const { items, missing } = toItems(t);
    if (items.length === 0) {
      toast.error("None of this template's exercises are in the library any more.");
      return;
    }
    onUse(items, t.name);
    setOpen(false);
    if (missing) toast.error(`${missing} exercise(s) in this template no longer exist in the library.`);
  };

  const remove = async (t: ExerciseTemplate) => {
    if (!window.confirm(`Delete the template "${t.name}"? Saved prescriptions are not affected.`)) return;
    setBusyId(t.id);
    try {
      await deleteTemplate(t.id);
      setTemplates((prev) => (prev || []).filter((x) => x.id !== t.id));
      toast("Template deleted.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete the template.");
    } finally {
      setBusyId(null);
    }
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      toast.error("Give the template a name.");
      return;
    }
    setSaving(true);
    try {
      const created = await createTemplate({
        name: trimmed,
        description: description.trim() || undefined,
        items: current.map((i) => ({
          exercise_id: i.exercise.id,
          sets: i.sets,
          reps: i.reps,
          hold: i.hold,
          frequency: i.frequency,
          note: i.note?.trim() || undefined,
        })),
      });
      setTemplates((prev) => [created, ...(prev || []).filter((x) => x.id !== created.id)]);
      setShowSave(false);
      setName("");
      setDescription("");
      toast(`Template "${created.name}" saved.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save the template.");
    } finally {
      setSaving(false);
    }
  };

  const count = templates?.length ?? 0;

  return (
    <div className="rounded-xl border border-line bg-card">
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex flex-1 cursor-pointer items-center gap-2 text-left text-sm font-semibold text-ink"
        >
          <LayoutTemplate className="h-4 w-4 text-logo-teal-ink" />
          <span className="flex-1">Templates{templates ? ` (${count})` : ""}</span>
          <span className="text-xs font-semibold text-grove">{open ? "Hide" : "Show"}</span>
        </button>
        {current.length > 0 && !showSave && (
          <button
            type="button"
            onClick={() => {
              setShowSave(true);
              setOpen(true);
            }}
            className="flex cursor-pointer items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-ink-2 hover:bg-muted"
          >
            <BookmarkPlus className="h-3.5 w-3.5" />
            Save as template
          </button>
        )}
      </div>

      {open && (
        <div className="border-t border-line">
          {showSave && (
            <form onSubmit={save} className="space-y-2 border-b border-line-soft p-3">
              <p className="text-xs text-muted-foreground">
                Saves the {current.length} {current.length === 1 ? "exercise" : "exercises"} on screen with their dose. No patient details are kept.
              </p>
              <input
                autoFocus
                value={name}
                maxLength={NAME_MAX}
                onChange={(e) => setName(e.target.value)}
                placeholder="Template name, e.g. ACL week 1 to 2"
                className="h-9 w-full rounded-[10px] border border-line bg-canvas/60 px-3 text-[13px] text-ink placeholder:text-[#8a8fa6] focus:border-grove focus:bg-card focus:outline-none focus:ring-2 focus:ring-grove/15"
              />
              <textarea
                rows={2}
                value={description}
                maxLength={DESCRIPTION_MAX}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="When to use it (optional)"
                className="w-full resize-y rounded-[10px] border border-line bg-canvas/60 px-3 py-2 text-[13px] text-ink placeholder:text-[#8a8fa6] focus:border-grove focus:bg-card focus:outline-none focus:ring-2 focus:ring-grove/15"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowSave(false)}
                  className="h-8 cursor-pointer rounded-lg px-3 text-xs font-semibold text-ink-2 hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex h-8 cursor-pointer items-center gap-1.5 rounded-lg bg-grove px-3 text-xs font-semibold text-white hover:bg-grove-hover disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Save template
                </button>
              </div>
            </form>
          )}

          {templates === null ? (
            <p className="px-3 py-3 text-xs text-muted-foreground">Loading templates...</p>
          ) : count === 0 ? (
            <p className="px-3 py-3 text-xs text-muted-foreground">
              No templates yet. Build a prescription, then use Save as template to reuse it.
            </p>
          ) : (
            <ul className="max-h-60 divide-y divide-line-soft overflow-y-auto">
              {templates.map((t) => (
                <li key={t.id} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {t.name}
                      <span className="ml-2 text-xs font-medium text-muted-foreground">
                        {t.items.length} {t.items.length === 1 ? "exercise" : "exercises"}
                      </span>
                      {t.is_global && (
                        <span className="ml-2 rounded bg-grove-wash px-1.5 py-0.5 text-[10px] font-bold uppercase text-grove">AV</span>
                      )}
                    </p>
                    {t.description && <p className="truncate text-xs text-muted-foreground">{t.description}</p>}
                  </div>
                  {!t.is_global && (
                    <button
                      type="button"
                      onClick={() => remove(t)}
                      disabled={busyId === t.id}
                      aria-label={`Delete template ${t.name}`}
                      className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-danger disabled:opacity-50"
                    >
                      {busyId === t.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => use(t)}
                    className="h-8 cursor-pointer rounded-lg border border-line px-3 text-xs font-semibold text-ink hover:border-grove hover:text-grove"
                  >
                    Use
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
