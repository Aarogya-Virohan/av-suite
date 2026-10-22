'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { ArrowLeft, ChevronRight, ClipboardList, Download, Link2, Loader2, Phone, Send, XCircle } from 'lucide-react';
import { api, ApiError, downloadFile } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate, formatDateTime, fullName } from '@/lib/format';
import { REFERRAL_LABELS } from '@/lib/severity';
import type { Assignment, AssignmentCreated, InstrumentId, Patient, PatientSummary, PatientTrend, ReferralAction } from '@/lib/types';
import { Avatar, Badge, Button, Card, CardHeader } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { useCan } from '@/components/staff/session-context';
import { AssignDrawer, LinkReady } from '@/components/screening/AssignDrawer';
import { DeleteDataPanel } from '@/components/screening/DeleteDataPanel';
import { TrendChart } from '@/components/screening/TrendChart';
import { PatientSchedules } from '@/components/screening/Schedules';
import {
  EmptyState,
  FlagChips,
  NoAccess,
  SessionStatusBadge,
  SeverityIndicator,
} from '@/components/screening/indicators';

function LinkStatus({ a }: { a: Assignment }) {
  switch (a.effective_status) {
    case 'active':
      return <Badge tone="active">Link active until {formatDate(a.expires_at)}</Badge>;
    case 'expired':
      return <Badge tone="warn">Link expired {formatDate(a.expires_at)}</Badge>;
    case 'completed':
      return <Badge tone="ok">All answered</Badge>;
    default:
      return <Badge tone="neutral">Cancelled</Badge>;
  }
}

function AssignmentCard({ a, patient }: { a: Assignment; patient: Patient }) {
  const canAssign = useCan('screening.assign');
  const qc = useQueryClient();
  const [reissued, setReissued] = useState<AssignmentCreated | null>(null);
  const started = a.sessions.some((s) => s.status !== 'pending' || s.answered_count > 0);
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['assignments', a.patient_id] });
    // A cancelled or renewed link changes whether a repeat is due.
    qc.invalidateQueries({ queryKey: ['schedules', a.patient_id] });
    qc.invalidateQueries({ queryKey: ['worklist'] });
    qc.invalidateQueries({ queryKey: ['due'] });
  };

  const cancel = useMutation({
    mutationFn: () => api.post<Assignment>(`/psychosocial/assignments/${a.id}/cancel`),
    onSuccess: () => {
      toast.success('Screener cancelled. The link no longer works.');
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const reissue = useMutation({
    mutationFn: () => api.post<AssignmentCreated>(`/psychosocial/assignments/${a.id}/link`, { expires_in_days: 7 }),
    onSuccess: (data) => {
      setReissued(data);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const open = a.status === 'active';

  return (
    <li className="rounded-2xl border border-line bg-card p-4 shadow-card sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">Sent {formatDateTime(a.created_at)}</p>
          <p className="text-xs text-muted">{a.assigned_by_name ? `by ${a.assigned_by_name}` : ''}</p>
        </div>
        <LinkStatus a={a} />
      </div>

      <ul className="mt-3 divide-y divide-line-soft">
        {a.sessions.map((s) => (
          <li key={s.id}>
            <Link href={`/sessions/${s.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3 hover:bg-canvas/50 sm:flex-nowrap">
              <span className="w-16 shrink-0 font-semibold text-ink">{s.short_name}</span>
              <span className="shrink-0">
                <SessionStatusBadge status={s.status} linkStatus={a.effective_status} />
              </span>
              <span className="min-w-0 flex-1">
                {s.status === 'completed' ? (
                  <span className="flex flex-wrap gap-x-4 gap-y-1">
                    {s.scales.map((scale) => (
                      <SeverityIndicator key={scale.scale_id} instrumentId={s.instrument_id} scale={scale} size="sm" />
                    ))}
                  </span>
                ) : s.status !== 'cancelled' ? (
                  <span className="text-[13px] text-muted">
                    {s.answered_count} of {s.total_items} answered
                  </span>
                ) : null}
              </span>
              <FlagChips referral={s.referral_flag} risk={s.risk_item_flag} partialRisk={s.partial_risk} />
              <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
            </Link>
          </li>
        ))}
      </ul>

      {open && canAssign ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-line-soft pt-3">
          <Button variant="secondary" className="h-9" onClick={() => reissue.mutate()} disabled={reissue.isPending}>
            {reissue.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
            New link
          </Button>
          {!started ? (
            <Button variant="ghost" className="h-9 text-danger hover:bg-danger-wash" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
              {cancel.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
              Cancel screener
            </Button>
          ) : null}
        </div>
      ) : null}

      <SlideOver isOpen={reissued !== null} onClose={() => setReissued(null)} title="New link" subtitle="The previous link has stopped working.">
        {reissued ? <LinkReady patient={patient} created={reissued} /> : null}
      </SlideOver>
    </li>
  );
}

export default function PatientPage() {
  const { id } = useParams<{ id: string }>();
  const canViewPatient = useCan('patients.view');
  const canAssign = useCan('screening.assign');
  const canViewResults = useCan('screening.view');
  const canDelete = useCan('screening.delete');
  const [assigning, setAssigning] = useState(false);
  const [preselect, setPreselect] = useState<InstrumentId[]>([]);
  const openAssign = (instruments: InstrumentId[] = []) => {
    setPreselect(instruments);
    setAssigning(true);
  };

  const patient = useQuery({
    queryKey: ['patient', id],
    enabled: canViewPatient,
    queryFn: () => api.get<Patient>(`/patients/${id}`),
  });
  const summary = useQuery({
    queryKey: ['summary', id],
    enabled: canViewResults,
    queryFn: () => api.get<PatientSummary>(`/patients/${id}/psychosocial/summary`),
  });
  const assignments = useQuery({
    queryKey: ['assignments', id],
    enabled: canViewResults,
    queryFn: () => api.get<Assignment[]>(`/patients/${id}/psychosocial/sessions`),
  });
  const referrals = useQuery({
    queryKey: ['patient-referrals', id],
    enabled: canViewResults,
    queryFn: () => api.get<ReferralAction[]>(`/patients/${id}/psychosocial/referral-actions`),
  });
  const trend = useQuery({
    queryKey: ['trend', id],
    enabled: canViewResults,
    queryFn: () => api.get<PatientTrend>(`/patients/${id}/psychosocial/trend`),
  });
  const [downloading, setDownloading] = useState(false);

  if (!canViewPatient) return <NoAccess what="patients" />;
  if (patient.isPending) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </div>
    );
  }
  if (patient.isError) {
    const notFound = patient.error instanceof ApiError && patient.error.status === 404;
    return <EmptyState icon={ClipboardList} title={notFound ? 'Patient not found' : 'Could not load patient'}>{patient.error.message}</EmptyState>;
  }

  const p = patient.data;
  const name = fullName(p);

  const downloadReport = async () => {
    setDownloading(true);
    try {
      const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'patient';
      const day = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      await downloadFile(`/patients/${p.id}/psychosocial/report.pdf`, `screening-summary-${slug}-${day}.pdf`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not create the PDF.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Link href="/patients" className="inline-flex items-center gap-1.5 text-sm font-semibold text-grove hover:text-grove-hover">
        <ArrowLeft className="h-4 w-4" />
        Patients
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Avatar name={name} size={52} />
          <div>
            <h1 className="font-display text-[26px] font-bold tracking-tight text-ink">{name}</h1>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
              {p.phone ? (
                <>
                  <Phone className="h-3.5 w-3.5" aria-hidden="true" />
                  {p.phone}
                </>
              ) : (
                'No phone on file'
              )}
              {p.age ? <> · {p.age} yrs</> : null}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canViewResults ? (
            <Button variant="secondary" onClick={downloadReport} disabled={downloading}>
              {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              PDF summary
            </Button>
          ) : null}
          {canAssign ? (
            <Button onClick={() => openAssign()}>
              <Send className="h-4 w-4" />
              Send screener
            </Button>
          ) : null}
        </div>
      </div>

      {canAssign ? <PatientSchedules patientId={p.id} onSendDue={openAssign} /> : null}

      {!canViewResults ? (
        <Card className="p-5 text-sm text-ink-2">
          You can send screeners, but results are visible only to treating physiotherapists with access to
          screening results.
        </Card>
      ) : (
        <>
          <section aria-labelledby="latest-h">
            <h2 id="latest-h" className="mb-3 font-display text-[15.5px] font-bold text-ink">
              Latest results
            </h2>
            {summary.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Loading" />
            ) : summary.data && summary.data.latest.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {summary.data.latest.map((s) => (
                  <Link
                    key={s.id}
                    href={`/sessions/${s.id}`}
                    className={cn(
                      'rounded-2xl border bg-card p-4 shadow-card transition-colors hover:border-slate-300',
                      s.risk_item_flag ? 'border-danger/50' : 'border-line',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold text-ink">{s.short_name}</p>
                      <p className="text-xs text-muted">{formatDate(s.completed_at)}</p>
                    </div>
                    <div className="mt-3 space-y-3">
                      {s.scales.map((scale) => (
                        <div key={scale.scale_id}>
                          {s.scales.length > 1 ? <p className="mb-1 text-xs text-muted">{scale.label.replace('DASS-21 ', '')} · {scale.score}</p> : <p className="mb-1 font-display text-2xl font-bold tabular-nums text-ink">{scale.score}<span className="ml-1 text-sm font-semibold text-muted">/ {scale.max_score}</span></p>}
                          <SeverityIndicator instrumentId={s.instrument_id} scale={scale} />
                        </div>
                      ))}
                    </div>
                    <div className="mt-3">
                      <FlagChips referral={s.referral_flag} risk={s.risk_item_flag} />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="rounded-2xl border border-dashed border-line bg-card/60 p-5 text-sm text-muted">No completed screenings yet.</p>
            )}
          </section>

          {trend.data && trend.data.series.length > 0 ? (
            <section aria-labelledby="trend-h">
              <h2 id="trend-h" className="mb-3 font-display text-[15.5px] font-bold text-ink">
                Score trend
              </h2>
              <div className="grid gap-4 xl:grid-cols-2">
                {trend.data.series.map((s) => (
                  <TrendChart key={`${s.instrument_id}-${s.scale_id}`} series={s} />
                ))}
              </div>
            </section>
          ) : null}

          <section aria-labelledby="history-h">
            <h2 id="history-h" className="mb-3 font-display text-[15.5px] font-bold text-ink">
              Screening history
            </h2>
            {assignments.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Loading" />
            ) : assignments.isError ? (
              <p className="text-sm text-danger">{assignments.error.message}</p>
            ) : assignments.data.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No screeners sent yet"
                action={canAssign ? <Button onClick={() => openAssign()}>Send screener</Button> : undefined}
              >
                Send PHQ-9, GAD-7 or DASS-21. The patient answers on their phone.
              </EmptyState>
            ) : (
              <ul className="space-y-3">
                {assignments.data.map((a) => (
                  <AssignmentCard key={a.id} a={a} patient={p} />
                ))}
              </ul>
            )}
          </section>

          {referrals.data && referrals.data.length > 0 ? (
            <Card className="p-5">
              <CardHeader title="Referral history" />
              <ol className="space-y-2.5">
                {referrals.data.map((r) => (
                  <li key={r.id} className="text-sm">
                    <span className="font-semibold text-ink">{REFERRAL_LABELS[r.action]}</span>
                    {r.note ? <span className="text-ink-2"> · {r.note}</span> : null}
                    <span className="block text-xs text-muted">
                      {r.recorded_by_name ?? 'Former staff member'} · {formatDateTime(r.recorded_at)}
                    </span>
                  </li>
                ))}
              </ol>
            </Card>
          ) : null}
        </>
      )}

      {canDelete ? <DeleteDataPanel patientId={p.id} patientName={name} /> : null}

      {canAssign ? (
        <AssignDrawer patient={p} open={assigning} onClose={() => setAssigning(false)} initialSelected={preselect} />
      ) : null}
    </div>
  );
}
