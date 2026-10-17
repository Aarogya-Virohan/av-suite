'use client';

import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Activity, Baby, FileCheck, Heart, Loader2, Lock, Plus, Save, Stethoscope, Zap } from 'lucide-react';
import { SoapAssessment } from '../../../types/api';
import { useAssessments, useCreateAssessment, useUpdateAssessment } from '../../assessments/api';
import { useAuthStore } from '../../../store';
import { Badge, Button, Card, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

/*
 * Rewritten after verifying against the API (Decisions.md D-019):
 * - "Draft (Autosaving)" / "autosaved every 2 seconds" was shown but the
 *   autosave function was empty: nothing was saved until Finalize. There is now
 *   a real "Save draft", an "unsaved changes" marker and a leave-page warning.
 * - The pain VAS (default 6) was never sent. It now starts unset and is saved
 *   in form_data.pain_vas.
 * - Chip labels did not match the stored values (Neuro saved "chiropractic",
 *   Cardio "osteopathy", ...). The backend enum lists ortho/neuro/... but the
 *   database enum does not contain them (500 on save, L-25), so the area is
 *   stored in form_data.area and specialty stays "physiotherapy".
 * - "Finalized" was read from finalized_at, which the API never returns, so a
 *   finalized note still looked like a draft. It now uses `finalized`.
 * - "Re-open (Admin Only)" always failed: the backend never edits finalized
 *   notes. Removed; corrections go in a new note.
 * - Only the first note was ever shown; there is now a note list and "New note".
 */

const AREAS = [
  { key: 'ortho', label: 'Ortho', icon: Activity },
  { key: 'neuro', label: 'Neuro', icon: Stethoscope },
  { key: 'cardiopulm', label: 'Cardio-pulmonary', icon: Heart },
  { key: 'sports', label: 'Sports', icon: Zap },
  { key: 'paeds', label: 'Paediatrics', icon: Baby },
  { key: 'general', label: 'General', icon: FileCheck },
] as const;

const SOAP_FIELDS = [
  { key: 'subjective', label: 'Subjective (S)', placeholder: 'Patient reported symptoms, pain history, and limitations...' },
  { key: 'objective', label: 'Objective (O)', placeholder: 'Physical findings, ROM tests, posture analysis...' },
  { key: 'assessment', label: 'Assessment (A)', placeholder: 'Clinical impression and progress comparison...' },
  { key: 'plan', label: 'Plan (P)', placeholder: 'Treatment goals, frequency of visits, home routine...' },
] as const;

type Draft = {
  id?: string;
  diagnosis: string;
  area: string | null;
  pain_vas: number | null;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  finalized: boolean;
};

const emptyDraft = (): Draft => ({
  diagnosis: '',
  area: null,
  pain_vas: null,
  subjective: '',
  objective: '',
  assessment: '',
  plan: '',
  finalized: false,
});

function toDraft(note: SoapAssessment): Draft {
  const f = (note.form_data || {}) as Record<string, any>;
  return {
    id: note.id,
    diagnosis: note.diagnosis || '',
    area: typeof f.area === 'string' ? f.area : null,
    pain_vas: typeof f.pain_vas === 'number' ? f.pain_vas : null,
    subjective: String(f.subjective || ''),
    objective: String(f.objective || ''),
    assessment: String(f.assessment || ''),
    plan: String(f.plan || ''),
    finalized: !!note.finalized,
  };
}

const noteDateFormat = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
const fmt = (v?: string) => (v ? noteDateFormat.format(new Date(v)) : '');

function painTone(v: number) {
  if (v <= 3) return 'border-ok bg-ok text-white';
  if (v <= 6) return 'border-warn bg-warn text-white';
  return 'border-danger bg-danger text-white';
}

export function SoapNotesTab({ patientId, isReassessmentOnly = false }: { patientId: string; isReassessmentOnly?: boolean }) {
  const { data: assessmentsResponse, isLoading } = useAssessments(patientId);
  const createAssessment = useCreateAssessment();
  const updateAssessment = useUpdateAssessment();

  const notes = useMemo(
    () =>
      ((assessmentsResponse?.data || []) as SoapAssessment[])
        .filter((a) => !!a.is_reassessment === isReassessmentOnly)
        .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))),
    [assessmentsResponse?.data, isReassessmentOnly],
  );

  const [selectedId, setSelectedId] = useState<string | 'new' | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [dirty, setDirty] = useState(false);

  // Default to the latest note once loaded, or a new note if there are none.
  React.useEffect(() => {
    if (selectedId !== null || isLoading) return;
    if (notes.length) {
      setSelectedId(notes[0].id);
      setDraft(toDraft(notes[0]));
    } else {
      setSelectedId('new');
      setDraft(emptyDraft());
    }
  }, [notes, isLoading, selectedId]);

  // Warn before leaving the page with unsaved text.
  React.useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const isFinalized = draft.finalized;
  const busy = createAssessment.isPending || updateAssessment.isPending;
  const title = isReassessmentOnly ? 'Re-assessment' : 'SOAP Assessment';

  const confirmDiscard = () => !dirty || window.confirm('You have unsaved changes in this note. Discard them?');

  const openNote = (note: SoapAssessment) => {
    if (note.id === selectedId || !confirmDiscard()) return;
    setSelectedId(note.id);
    setDraft(toDraft(note));
    setDirty(false);
  };

  const startNew = () => {
    if (!confirmDiscard()) return;
    setSelectedId('new');
    setDraft(emptyDraft());
    setDirty(false);
  };

  const edit = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    if (isFinalized) return;
    setDraft((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const hasContent = !!(draft.diagnosis.trim() || draft.subjective.trim() || draft.objective.trim() || draft.assessment.trim() || draft.plan.trim());

  const save = async (finalize: boolean) => {
    if (!hasContent) {
      toast.error('Write something in the note before saving');
      return;
    }
    if (finalize && !window.confirm('Finalize this note? Finalized notes are locked and cannot be edited. Corrections go in a new note.')) {
      return;
    }
    const payload = {
      patient_id: patientId,
      therapist_id: useAuthStore.getState().userId || undefined,
      specialty: 'physiotherapy',
      diagnosis: draft.diagnosis.trim() || null,
      is_reassessment: isReassessmentOnly,
      finalized: finalize,
      form_data: {
        subjective: draft.subjective,
        objective: draft.objective,
        assessment: draft.assessment,
        plan: draft.plan,
        area: draft.area,
        pain_vas: draft.pain_vas,
      },
    };
    try {
      const saved: SoapAssessment = draft.id
        ? await updateAssessment.mutateAsync({ id: draft.id, values: payload })
        : await createAssessment.mutateAsync(payload);
      setSelectedId(saved.id);
      setDraft(toDraft(saved));
      setDirty(false);
      toast.success(finalize ? `${title} finalized and locked` : 'Draft saved');
    } catch (err: any) {
      toast.error(err?.message || 'Failed to save note');
    }
  };

  if (isLoading) {
    return (
      <Card className="flex items-center gap-2 p-6 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-grove" /> Loading notes...
      </Card>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
      {/* Note history */}
      <Card className="h-fit space-y-2 p-3">
        <Button variant="secondary" className="h-9 w-full" onClick={startNew}>
          <Plus className="h-4 w-4" /> New note
        </Button>
        {selectedId === 'new' && (
          <div className="rounded-lg border border-grove/30 bg-grove-wash px-3 py-2 text-xs font-semibold text-grove">New note (not saved yet)</div>
        )}
        {notes.length === 0 && <p className="px-1 py-2 text-xs text-muted">No {title.toLowerCase()} notes yet.</p>}
        {notes.map((n) => {
          const area = AREAS.find((a) => a.key === (n.form_data as any)?.area)?.label;
          return (
            <button
              key={n.id}
              type="button"
              onClick={() => openNote(n)}
              className={cn(
                'w-full cursor-pointer rounded-lg border px-3 py-2 text-left transition-colors',
                selectedId === n.id ? 'border-grove bg-grove-wash' : 'border-line hover:bg-canvas',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-ink">{fmt(n.created_at)}</span>
                {n.finalized ? <Lock className="h-3.5 w-3.5 text-ok" aria-label="Finalized" /> : <span className="text-[10px] font-bold uppercase text-warn">Draft</span>}
              </div>
              <p className="mt-0.5 truncate text-xs text-muted">{n.diagnosis || area || 'No diagnosis'}</p>
            </button>
          );
        })}
      </Card>

      {/* Editor */}
      <div className="space-y-5">
        <Card className="flex flex-col items-start justify-between gap-4 p-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-base font-bold text-ink">{title}</h3>
              {isFinalized ? (
                <Badge tone="ok">Finalized</Badge>
              ) : dirty ? (
                <Badge tone="warn">Unsaved changes</Badge>
              ) : draft.id ? (
                <Badge tone="info">Draft saved</Badge>
              ) : (
                <Badge tone="neutral">New</Badge>
              )}
            </div>
            <p className="mt-0.5 text-xs text-muted">
              {isFinalized
                ? 'Finalized notes are locked. Start a new note for corrections or follow-up.'
                : 'Save a draft any time; finalize when the note is complete.'}
            </p>
          </div>
          {!isFinalized && (
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => save(false)} disabled={busy || !dirty}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save draft
              </Button>
              <Button onClick={() => save(true)} disabled={busy}>
                <FileCheck className="h-4 w-4" />
                Finalize & lock
              </Button>
            </div>
          )}
        </Card>

        <Card className="space-y-5 p-5">
          <div>
            <FieldLabel>Clinical area</FieldLabel>
            <div className="flex flex-wrap items-center gap-2">
              {AREAS.map((a) => {
                const Icon = a.icon;
                const active = draft.area === a.key;
                return (
                  <button
                    key={a.key}
                    type="button"
                    disabled={isFinalized}
                    aria-pressed={active}
                    onClick={() => edit('area', active ? null : a.key)}
                    className={cn(
                      'flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
                      active ? 'border-grove bg-grove text-white' : 'border-line bg-card text-ink-2 hover:border-grove',
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {a.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <FieldLabel>Pain VAS (0 to 10)</FieldLabel>
              {draft.pain_vas !== null && !isFinalized && (
                <button type="button" onClick={() => edit('pain_vas', null)} className="cursor-pointer text-xs font-semibold text-muted hover:text-ink">
                  Clear
                </button>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {Array.from({ length: 11 }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  disabled={isFinalized}
                  aria-pressed={draft.pain_vas === i}
                  onClick={() => edit('pain_vas', i)}
                  className={cn(
                    'h-9 w-9 cursor-pointer rounded-lg border text-xs font-bold transition-colors disabled:cursor-not-allowed',
                    draft.pain_vas === i ? painTone(i) : 'border-line bg-card text-ink-2 hover:bg-canvas',
                  )}
                >
                  {i}
                </button>
              ))}
              {draft.pain_vas === null && <span className="ml-1 text-xs text-muted">Not recorded</span>}
            </div>
          </div>

          <div>
            <FieldLabel htmlFor={`dx-${isReassessmentOnly}`}>Clinical Diagnosis</FieldLabel>
            <input
              id={`dx-${isReassessmentOnly}`}
              type="text"
              disabled={isFinalized}
              value={draft.diagnosis}
              onChange={(e) => edit('diagnosis', e.target.value)}
              placeholder="e.g. Lumbar disc herniation L4-L5"
              className={inputClass}
            />
          </div>

          {SOAP_FIELDS.map((f) => (
            <div key={f.key}>
              <label htmlFor={`${f.key}-${isReassessmentOnly}`} className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-grove">
                {f.label}
              </label>
              <textarea
                id={`${f.key}-${isReassessmentOnly}`}
                rows={3}
                disabled={isFinalized}
                value={draft[f.key]}
                onChange={(e) => edit(f.key, e.target.value)}
                placeholder={f.placeholder}
                className={cn(inputClass, 'h-auto py-2')}
              />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
