'use client';

import React from 'react';
import { Activity, ClipboardList, Minus, Printer, TrendingDown, TrendingUp } from 'lucide-react';
import { useTreatments } from '../../treatments/api';
import { useAssessments } from '../../assessments/api';
import type { SoapAssessment } from '../../../types/api';
import { Badge, Button, Card, KpiCard } from '../../../components/ui/brand';

/*
 * Fixes:
 * - "Export Progression PDF" called /documents/{patientId}/download, i.e. the
 *   patient id as a document id: always 404 (verified), and it never saved a
 *   file even on success. There is no progression PDF endpoint, so the tab now
 *   prints itself (browser "Save as PDF") from the data shown.
 * - A worse pain score showed as "Pain Reduction ▼ -3 pts". The change is now
 *   labelled improved / worse / no change.
 * - Baseline and latest re-assessment assumed the API order and picked any
 *   note. Notes are sorted by date; baseline is the first SOAP assessment and
 *   "latest" is the most recent re-assessment.
 * - Sessions are sorted by date before taking initial/current pain (the API
 *   does not order them, Decisions.md D-012).
 */

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
const fmt = (v?: string | null) => (v ? dateFmt.format(new Date(v)) : '');

function NoteSummary({ note, empty }: { note: SoapAssessment | null; empty: string }) {
  if (!note) return <p className="text-sm italic text-muted">{empty}</p>;
  const f = (note.form_data || {}) as Record<string, any>;
  const rows: [string, string][] = [
    ['Diagnosis', note.diagnosis || ''],
    ['Pain VAS', typeof f.pain_vas === 'number' ? `${f.pain_vas}/10` : ''],
    ['Subjective', f.subjective || ''],
    ['Objective', f.objective || ''],
    ['Assessment', f.assessment || ''],
  ];
  return (
    <div className="space-y-1.5 text-sm">
      <p className="text-xs text-muted">
        {fmt(note.created_at)} · {note.finalized ? 'Finalized' : 'Draft'}
      </p>
      {rows.map(([label, value]) => (
        <p key={label} className="text-ink-2">
          <span className="font-semibold text-ink">{label}: </span>
          {value || <span className="italic text-slate-400">Not recorded</span>}
        </p>
      ))}
    </div>
  );
}

export function ProgressionTab({ patientId, patientName }: { patientId: string; patientName?: string }) {
  const { data: treatmentsResponse } = useTreatments(patientId);
  const sessions = treatmentsResponse?.data || [];

  const { data: assessmentsResponse } = useAssessments(patientId);
  const assessments = ((assessmentsResponse?.data || []) as SoapAssessment[])
    .slice()
    .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));

  const painScores = [...sessions]
    .sort(
      (a: any, b: any) =>
        String(a.treatment_date ?? '').localeCompare(String(b.treatment_date ?? '')) ||
        String(a.created_at ?? '').localeCompare(String(b.created_at ?? '')),
    )
    .filter((s: any) => s.pain_score != null)
    .map((s: any) => s.pain_score as number);

  const initialPain = painScores.length > 0 ? painScores[0] : null;
  const currentPain = painScores.length > 0 ? painScores[painScores.length - 1] : null;
  const delta = initialPain !== null && currentPain !== null && painScores.length > 1 ? initialPain - currentPain : null;

  const baseline = assessments.find((a) => !a.is_reassessment) ?? null;
  const latestReassessment = [...assessments].reverse().find((a) => a.is_reassessment) ?? null;

  const changeLabel =
    delta === null ? 'Not enough data' : delta > 0 ? `Improved by ${delta}` : delta < 0 ? `Worse by ${-delta}` : 'No change';
  const ChangeIcon = delta === null || delta === 0 ? Minus : delta > 0 ? TrendingDown : TrendingUp;

  return (
    <div className="print-area space-y-5">
      {/* Printed reports must identify the patient. */}
      <p className="hidden text-sm text-ink print:block">
        <strong>{patientName || 'Patient'}</strong> · Progression report printed {fmt(new Date().toISOString())}
      </p>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-base font-bold text-ink">Clinical Progression</h3>
          <p className="text-xs text-muted">Pain trend from recorded sessions and SOAP assessments</p>
        </div>
        <Button variant="secondary" className="no-print" onClick={() => window.print()}>
          <Printer className="h-4 w-4" />
          <span>Print / Save PDF</span>
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <KpiCard label="Sessions" value={sessions.length} icon={Activity} tone="teal" />
        <KpiCard label="Assessments" value={assessments.length} icon={ClipboardList} tone="info" />
        <KpiCard label="Initial pain" value={initialPain !== null ? `${initialPain}/10` : 'N/A'} icon={Activity} tone="danger" />
        <KpiCard label="Current pain" value={currentPain !== null ? `${currentPain}/10` : 'N/A'} icon={Activity} tone="grove" />
        <Card className="col-span-2 flex flex-col justify-between p-5 md:col-span-1">
          <span className="text-[12.5px] font-medium text-muted">Pain change</span>
          <div className="mt-3 flex items-center gap-2">
            <ChangeIcon className={delta !== null && delta > 0 ? 'h-5 w-5 text-ok' : delta !== null && delta < 0 ? 'h-5 w-5 text-danger' : 'h-5 w-5 text-muted'} />
            <Badge tone={delta === null || delta === 0 ? 'neutral' : delta > 0 ? 'ok' : 'danger'}>{changeLabel}</Badge>
          </div>
        </Card>
      </div>

      <Card className="space-y-4 p-6">
        <h4 className="font-display text-sm font-bold text-ink">Baseline vs latest re-assessment</h4>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2 rounded-xl border border-line bg-canvas p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-grove">Initial SOAP assessment</p>
            <NoteSummary note={baseline} empty="No SOAP assessment recorded yet." />
          </div>
          <div className="space-y-2 rounded-xl border border-logo-teal/30 bg-logo-teal-wash/50 p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-logo-teal-ink">Latest re-assessment</p>
            <NoteSummary note={latestReassessment} empty="No re-assessments recorded yet." />
          </div>
        </div>
      </Card>
    </div>
  );
}
