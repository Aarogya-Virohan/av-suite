"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ClipboardList, Download, FilePlus2, History, Loader2, Save } from "lucide-react";
import { Patient, PrescriptionItem, SavedPrescription } from "@/types/exercise";
import {
  createPrescription,
  downloadPrescriptionPDF,
  fetchNoteSuggestions,
  fetchPatients,
  fetchPrescriptions,
  type NoteSuggestions,
  mapBackendExerciseToFrontend,
  saveBlob,
  updatePrescription,
} from "@/lib/api";
import { toast } from "@/components/ui/toaster";
import { ExerciseRow } from "./ExerciseRow";
import { PatientPicker } from "./PatientPicker";
import { AddPatientForm } from "./AddPatientForm";
import { QuickPicks, addPhrase } from "./QuickPicks";
import { TemplatesPanel } from "./TemplatesPanel";

interface PrescriptionBuilderProps {
  prescription: PrescriptionItem[];
  onChange: (item: PrescriptionItem) => void;
  onRemove: (id: string) => void;
  onReplace: (items: PrescriptionItem[]) => void;
}

// Same text the builder has sent with every new prescription since the
// start; now only the starting value of an editable field.
const DEFAULT_PHYSIO_NOTES =
  "Please follow sets and reps instructions carefully. Reach out if you feel acute discomfort.";
const GUIDANCE_MAX = 2000;

/** What was last saved, to tell "saved" from "changed since". */
interface SavedState {
  rxId: string;
  patientId: string;
  key: string;
}

function itemsKey(items: PrescriptionItem[], guidance: string): string {
  return JSON.stringify([
    items.map((i) => [i.exercise.id, i.sets, i.reps, i.hold, i.frequency, (i.note || "").trim()]),
    guidance.trim(),
  ]);
}

function toPayload(items: PrescriptionItem[]) {
  return items.map((i) => ({
    exercise_id: i.exercise.id,
    sets: i.sets,
    reps: i.reps,
    hold: i.hold,
    frequency: i.frequency,
    note: i.note?.trim() || undefined,
  }));
}

const dateFmt = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "Asia/Kolkata",
});

function rxDate(iso: string): string {
  return dateFmt.format(new Date(iso));
}

export function PrescriptionBuilder({ prescription, onChange, onRemove, onReplace }: PrescriptionBuilderProps) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientId, setPatientId] = useState("");
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [history, setHistory] = useState<SavedPrescription[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [saved, setSaved] = useState<SavedState | null>(null);
  const [busy, setBusy] = useState<"save" | "pdf" | null>(null);
  const [guidance, setGuidance] = useState(DEFAULT_PHYSIO_NOTES);
  const [suggestions, setSuggestions] = useState<NoteSuggestions>({ notes: [], guidance: [] });

  const key = useMemo(() => itemsKey(prescription, guidance), [prescription, guidance]);
  const editingRxId = saved && saved.patientId === patientId ? saved.rxId : null;
  const isSaved = !!editingRxId && saved?.key === key;
  const editingRx = editingRxId ? history?.find((h) => h.id === editingRxId) : undefined;

  // Patients once.
  useEffect(() => {
    fetchPatients()
      .then(setPatients)
      .catch((err) => toast.error(err instanceof Error ? err.message : "Could not load patients."))
      .finally(() => setPatientsLoading(false));
  }, []);

  // Quick-pick phrases from this clinic's earlier prescriptions. Optional:
  // without them the fields still work as plain text.
  const loadSuggestions = useCallback(() => {
    fetchNoteSuggestions()
      .then(setSuggestions)
      .catch(() => setSuggestions({ notes: [], guidance: [] }));
  }, []);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  // History of the chosen patient.
  const loadHistory = useCallback(async (id: string) => {
    try {
      setHistory(await fetchPrescriptions(id));
    } catch {
      setHistory([]);
    }
  }, []);

  const selectPatient = (id: string) => {
    setPatientId(id);
    setHistory(null);
    setHistoryOpen(false);
    if (id) loadHistory(id);
  };

  // Warn before leaving with unsaved work.
  useEffect(() => {
    if (prescription.length === 0 || isSaved) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [prescription.length, isSaved]);

  const openSaved = (rx: SavedPrescription) => {
    if (prescription.length > 0 && !isSaved) {
      const ok = window.confirm("Replace the exercises on screen with this saved prescription? Unsaved changes will be lost.");
      if (!ok) return;
    }
    const items: PrescriptionItem[] = [];
    let missing = 0;
    for (const it of rx.items) {
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
    const savedGuidance = rx.physio_notes ?? "";
    onReplace(items);
    setGuidance(savedGuidance);
    setSaved({ rxId: rx.id, patientId: rx.patient_id, key: itemsKey(items, savedGuidance) });
    setHistoryOpen(false);
    if (missing) toast.error(`${missing} exercise(s) in this prescription no longer exist in the library.`);
  };

  const startNew = () => {
    if (prescription.length > 0 && !isSaved) {
      const ok = window.confirm("Clear the exercises on screen? Unsaved changes will be lost.");
      if (!ok) return;
    }
    setSaved(null);
    setGuidance(DEFAULT_PHYSIO_NOTES);
    onReplace([]);
  };

  /** A template fills a NEW prescription (EL-D-009): it never overwrites a
   * saved one, so the saved link is dropped. The guidance text is kept. */
  const applyTemplate = (items: PrescriptionItem[], name: string) => {
    if (prescription.length > 0 && !isSaved) {
      const ok = window.confirm(`Replace the exercises on screen with the template "${name}"? Unsaved changes will be lost.`);
      if (!ok) return;
    }
    setSaved(null);
    onReplace(items);
    toast(`Template "${name}" added. Adjust the dose for this patient, then save.`);
  };

  const validate = (): boolean => {
    if (!patientId) {
      toast.error("Choose a patient first.");
      return false;
    }
    if (prescription.length === 0) {
      toast.error("Add at least one exercise.");
      return false;
    }
    return true;
  };

  /** Create or update; returns the prescription id. */
  const persist = async (): Promise<string> => {
    const items = toPayload(prescription);
    let id: string;
    const notes = guidance.trim();
    if (editingRxId) {
      // "" clears the guidance; the PDF then leaves the box out.
      await updatePrescription(editingRxId, { items, physio_notes: notes });
      id = editingRxId;
    } else {
      const created = await createPrescription({
        patient_id: patientId,
        physio_notes: notes || undefined,
        status: "active",
        items,
      });
      id = created.id;
    }
    setSaved({ rxId: id, patientId, key });
    loadHistory(patientId);
    loadSuggestions();
    return id;
  };

  const handleSave = async () => {
    if (!validate()) return;
    setBusy("save");
    try {
      const wasEditing = !!editingRxId;
      await persist();
      toast(wasEditing ? "Prescription updated." : "Prescription saved.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save the prescription.");
    } finally {
      setBusy(null);
    }
  };

  const handlePdf = async () => {
    if (!validate()) return;
    setBusy("pdf");
    try {
      const id = isSaved && editingRxId ? editingRxId : await persist();
      const { blob, filename } = await downloadPrescriptionPDF(id);
      saveBlob(blob, filename);
      toast(`Saved and downloaded ${filename}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create the PDF.");
    } finally {
      setBusy(null);
    }
  };

  const status = !patientId
    ? null
    : editingRxId
      ? isSaved
        ? { tone: "ok", text: `Saved · ${editingRx ? rxDate(editingRx.created_at) : ""}` }
        : { tone: "warn", text: "Editing a saved prescription · unsaved changes" }
      : prescription.length
        ? { tone: "muted", text: "New prescription · not saved yet" }
        : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex shrink-0 items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-display text-xl font-bold text-ink">
          <ClipboardList className="h-5 w-5 text-grove" />
          Prescription
        </h2>
        {prescription.length > 0 && (
          <button
            type="button"
            onClick={startNew}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold text-ink-2 hover:bg-muted"
          >
            <FilePlus2 className="h-3.5 w-3.5" />
            Start new
          </button>
        )}
      </div>

      {/* Patient */}
      <div className="mb-4 shrink-0 space-y-2">
        <span className="block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Patient</span>
        {showAddPatient ? (
          <AddPatientForm
            onCancel={() => setShowAddPatient(false)}
            onCreated={(p) => {
              setPatients((prev) => [p, ...prev]);
              selectPatient(p.id);
              setShowAddPatient(false);
              toast(`${p.first_name} ${p.last_name} added.`);
            }}
          />
        ) : (
          <PatientPicker
            patients={patients}
            value={patientId}
            onChange={selectPatient}
            onAddNew={() => setShowAddPatient(true)}
            loading={patientsLoading}
          />
        )}

        {patientId && !showAddPatient && history && history.length > 0 && (
          <div className="rounded-xl border border-line bg-card">
            <button
              type="button"
              onClick={() => setHistoryOpen((o) => !o)}
              aria-expanded={historyOpen}
              className="flex w-full cursor-pointer items-center gap-2 px-3 py-2.5 text-left text-sm font-semibold text-ink"
            >
              <History className="h-4 w-4 text-logo-teal-ink" />
              <span className="flex-1">Previous prescriptions ({history.length})</span>
              <span className="text-xs font-semibold text-grove">{historyOpen ? "Hide" : "Show"}</span>
            </button>
            {historyOpen && (
              <ul className="max-h-60 divide-y divide-line-soft overflow-y-auto border-t border-line">
                {history.map((rx) => {
                  const names = rx.items
                    .map((i) => (i.exercise?.title as string | undefined)?.toLowerCase())
                    .filter(Boolean);
                  const current = rx.id === editingRxId;
                  return (
                    <li key={rx.id} className="flex items-center gap-3 px-3 py-2.5">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-ink">
                          {rxDate(rx.created_at)}
                          <span className="ml-2 text-xs font-medium text-muted-foreground">
                            {rx.items.length} {rx.items.length === 1 ? "exercise" : "exercises"}
                          </span>
                        </p>
                        <p className="truncate text-xs capitalize text-muted-foreground">{names.join(", ")}</p>
                      </div>
                      {current ? (
                        <span className="rounded-md bg-grove-wash px-2 py-1 text-xs font-semibold text-grove">Open</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => openSaved(rx)}
                          className="h-8 cursor-pointer rounded-lg border border-line px-3 text-xs font-semibold text-ink hover:border-grove hover:text-grove"
                        >
                          Open
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="mb-4 shrink-0">
        <TemplatesPanel current={prescription} onUse={applyTemplate} />
      </div>

      {/* Exercises */}
      {prescription.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line p-8 text-center">
          <span className="mb-3 grid h-11 w-11 place-items-center rounded-full bg-grove-wash text-grove">
            <ClipboardList className="h-5 w-5" />
          </span>
          <p className="font-semibold text-ink">No exercises yet</p>
          <p className="mt-1 max-w-[260px] text-sm text-muted-foreground">
            Add exercises from the library or use a template, then set the dose for each.
          </p>
        </div>
      ) : (
        <div className="-mr-2 min-h-0 flex-1 space-y-2.5 overflow-y-auto pb-4 pr-2">
          <ol className="space-y-2.5">
            {prescription.map((item, i) => (
              <ExerciseRow
                key={item.exercise.id}
                index={i + 1}
                item={item}
                onChange={onChange}
                onRemove={onRemove}
                noteSuggestions={suggestions.notes}
              />
            ))}
          </ol>

          <section className="space-y-2 rounded-2xl border border-line bg-card p-3.5 shadow-card">
            <label htmlFor="rx-guidance" className="block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
              Guidance for the patient
            </label>
            <textarea
              id="rx-guidance"
              rows={3}
              maxLength={GUIDANCE_MAX}
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              placeholder="Shown on the PDF under the exercises (optional)"
              className="w-full resize-y rounded-[10px] border border-line bg-canvas/60 px-3 py-2 text-[13px] leading-relaxed text-ink placeholder:text-[#8a8fa6] transition-colors focus:border-grove focus:bg-card focus:outline-none focus:ring-2 focus:ring-grove/15"
            />
            <QuickPicks
              label="Quick guidance"
              options={suggestions.guidance}
              current={guidance}
              onPick={(phrase) => setGuidance((g) => addPhrase(g, /[.!?]$/.test(phrase) ? phrase : `${phrase}.`, " ", GUIDANCE_MAX))}
            />
          </section>
        </div>
      )}

      {/* Actions */}
      <div className="sticky bottom-0 -mx-4 shrink-0 border-t border-line bg-canvas/95 px-4 pb-3 pt-3 backdrop-blur sm:-mx-6 sm:px-6 lg:static lg:mx-0 lg:bg-transparent lg:px-0 lg:pb-0 lg:backdrop-blur-none">
        {status && (
          <p
            className={`mb-2 text-xs font-semibold ${
              status.tone === "ok" ? "text-ok" : status.tone === "warn" ? "text-warn" : "text-muted-foreground"
            }`}
          >
            {status.text}
          </p>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={busy !== null || prescription.length === 0 || isSaved}
            className="flex h-11 flex-1 cursor-pointer items-center justify-center gap-2 rounded-[10px] border border-line bg-card text-sm font-semibold text-ink transition-colors hover:border-grove/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === "save" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {isSaved ? "Saved" : editingRxId ? "Save changes" : "Save"}
          </button>
          <button
            type="button"
            onClick={handlePdf}
            disabled={busy !== null || prescription.length === 0}
            className="flex h-11 flex-[1.6] cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-grove text-sm font-semibold text-white shadow-primary transition-colors hover:bg-grove-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === "pdf" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {busy === "pdf" ? "Preparing PDF..." : isSaved ? "Download PDF" : "Save & download PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}
