'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, ClipboardList, Loader2, Minus } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate, formatDateTime } from '@/lib/format';
import { deltaWords, REFERRAL_LABELS, scoreDelta } from '@/lib/severity';
import type { ReferralAction, ReferralActionKey, Scale, SessionDetail } from '@/lib/types';
import { Button, Card, CardHeader, FieldLabel, inputClass } from '@/components/ui/brand';
import { useCan } from '@/components/staff/session-context';
import {
  EmptyState,
  FlagChips,
  InfoNote,
  NoAccess,
  RiskBanner,
  SessionStatusBadge,
  SeverityIndicator,
} from '@/components/screening/indicators';

function Delta({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  const Icon = delta === 0 ? Minus : delta < 0 ? ArrowDownRight : ArrowUpRight;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-ink-2">
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {deltaWords(delta)}
    </span>
  );
}

function ScaleCard({
  detail,
  scale,
  baseline,
}: {
  detail: SessionDetail;
  scale: Scale;
  baseline?: Scale;
}) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-semibold text-muted">{scale.label}</p>
        {scale.referral ? (
          <span className="rounded-full bg-danger-wash px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-danger">
            At referral level
          </span>
        ) : null}
      </div>
      <p className="mt-2 font-display text-[34px] font-bold leading-none tracking-tight text-ink tabular-nums">
        {scale.score}
        <span className="ml-1 text-base font-semibold text-muted">/ {scale.max_score}</span>
      </p>
      <div className="mt-4">
        <SeverityIndicator instrumentId={detail.session.instrument_id} scale={scale} />
      </div>
      {baseline ? (
        <div className="mt-4 border-t border-line-soft pt-3 text-xs text-muted">
          <p>
            Baseline {formatDate(detail.baseline?.completed_at)}: <span className="font-semibold text-ink-2 tabular-nums">{baseline.score}</span>{' '}
            {baseline.band_label}
          </p>
          <div className="mt-1">
            <Delta delta={scoreDelta(scale, baseline)} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ReferralLog({ detail }: { detail: SessionDetail }) {
  const canRefer = useCan('screening.refer');
  const qc = useQueryClient();
  const [action, setAction] = useState<ReferralActionKey | ''>('');
  const [note, setNote] = useState('');

  const save = useMutation({
    mutationFn: () =>
      api.post<ReferralAction>(`/psychosocial/sessions/${detail.session.id}/referral-actions`, {
        action,
        note: note.trim() || null,
      }),
    onSuccess: () => {
      toast.success('Referral action saved');
      setAction('');
      setNote('');
      qc.invalidateQueries({ queryKey: ['session', detail.session.id] });
      qc.invalidateQueries({ queryKey: ['patient-referrals', detail.session.patient_id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="p-5">
      <CardHeader title="Referral" />
      {detail.referral_actions.length === 0 ? (
        <p className="text-sm text-muted">No action recorded yet.</p>
      ) : (
        <ol className="space-y-3">
          {detail.referral_actions.map((a) => (
            <li key={a.id} className="rounded-xl border border-line-soft bg-canvas/60 p-3 text-sm">
              <p className="font-semibold text-ink">{REFERRAL_LABELS[a.action]}</p>
              {a.note ? <p className="mt-0.5 text-ink-2">{a.note}</p> : null}
              <p className="mt-1 text-xs text-muted">
                {a.recorded_by_name ?? 'Former staff member'} · {formatDateTime(a.recorded_at)}
              </p>
            </li>
          ))}
        </ol>
      )}

      {canRefer ? (
        <form
          className="mt-5 space-y-3 border-t border-line-soft pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (action) save.mutate();
          }}
        >
          <div>
            <FieldLabel htmlFor="ref-action">Record what you did</FieldLabel>
            <select
              id="ref-action"
              className={inputClass}
              value={action}
              onChange={(e) => setAction(e.target.value as ReferralActionKey)}
            >
              <option value="">Choose an action</option>
              {Object.entries(REFERRAL_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <FieldLabel htmlFor="ref-note">Note (optional)</FieldLabel>
            <textarea
              id="ref-note"
              rows={3}
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className={cn(inputClass, 'h-auto py-2')}
              placeholder="For example, who you referred to and when"
            />
          </div>
          <Button type="submit" disabled={!action || save.isPending}>
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save action
          </Button>
          <InfoNote>Saved actions cannot be edited. Add a new entry if something changes.</InfoNote>
        </form>
      ) : null}
    </Card>
  );
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const canView = useCan('screening.view');
  const query = useQuery({
    queryKey: ['session', id],
    enabled: canView,
    queryFn: () => api.get<SessionDetail>(`/psychosocial/sessions/${id}`),
  });

  if (!canView) return <NoAccess what="screening results" />;
  if (query.isPending) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </div>
    );
  }
  if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.status === 404;
    return (
      <EmptyState icon={ClipboardList} title={notFound ? 'Screening not found' : 'Could not load this screening'}>
        {notFound ? 'It may belong to another physiotherapist, or the link is wrong.' : query.error.message}
      </EmptyState>
    );
  }

  const d = query.data;
  const s = d.session;
  const item9 = d.responses.find((r) => r.item_id === 'phq9_9');
  const baselineByScale = new Map((d.baseline?.scales ?? []).map((b) => [b.scale_id, b]));
  const answered = d.responses.filter((r) => r.value !== null).length;

  return (
    <div className="space-y-6">
      <Link href={`/patients/${s.patient_id}`} className="inline-flex items-center gap-1.5 text-sm font-semibold text-grove hover:text-grove-hover">
        <ArrowLeft className="h-4 w-4" />
        {d.patient_name}
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight text-ink">
            {s.short_name} <span className="font-semibold text-muted">· {d.patient_name}</span>
          </h1>
          <p className="mt-1 text-sm text-muted">
            {d.instrument_name}
            {s.completed_at ? <> · completed {formatDateTime(s.completed_at)}</> : null}
            {d.is_baseline ? <> · baseline</> : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SessionStatusBadge status={s.status} />
          <FlagChips referral={s.referral_flag} risk={s.risk_item_flag} partialRisk={s.partial_risk} />
        </div>
      </div>

      {s.risk_item_flag || s.partial_risk ? (
        <RiskBanner answerLabel={item9?.answer_label ?? null} submitted={s.status === 'completed'} />
      ) : null}

      {s.status === 'completed' ? (
        <>
          <div className={cn('grid gap-4', s.scales.length > 1 ? 'md:grid-cols-3' : 'sm:max-w-sm')}>
            {s.scales.map((scale) => (
              <ScaleCard key={scale.scale_id} detail={d} scale={scale} baseline={baselineByScale.get(scale.scale_id)} />
            ))}
          </div>
          {d.reasons.length ? (
            <ul className="space-y-1 text-sm text-ink-2">
              {d.reasons.map((r) => (
                <li key={r} className="flex items-center gap-2">
                  <ArrowRight className="h-3.5 w-3.5 text-danger" aria-hidden="true" />
                  {r}
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : (
        <Card className="p-5 text-sm text-ink-2">
          {s.status === 'cancelled'
            ? 'This screener was cancelled before the patient finished it.'
            : `The patient has answered ${answered} of ${d.responses.length} questions. A score appears once they submit.`}
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <h2 className="font-display text-[15.5px] font-bold text-ink">Answers</h2>
            <p className="text-xs text-muted">Exactly as the patient answered, in order.</p>
          </div>
          <ol className="divide-y divide-line-soft">
            {d.responses.map((r) => (
              <li
                key={r.item_id}
                className={cn(
                  'grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3 gap-y-1 px-5 py-3 sm:grid-cols-[2rem_minmax(0,1fr)_minmax(0,14rem)]',
                  r.item_id === 'phq9_9' && (r.value ?? 0) > 0 && 'bg-danger-wash/50',
                )}
              >
                <span className="text-sm font-semibold text-muted tabular-nums">{r.scored ? r.number : '·'}</span>
                <span className="text-sm text-ink">
                  {r.text}
                  {!r.scored ? <span className="ml-1 text-xs text-muted">(not scored)</span> : null}
                </span>
                <span className="col-start-2 text-sm font-semibold text-ink-2 sm:col-start-3 sm:text-right">
                  {r.value === null ? (
                    <span className="font-normal text-muted">Not answered</span>
                  ) : (
                    <>
                      {r.answer_label} <span className="text-muted tabular-nums">({r.value})</span>
                    </>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </Card>

        <div className="space-y-6">
          {s.referral_flag ? <ReferralLog detail={d} /> : null}
          <InfoNote>
            Screening aid only, not a diagnosis. Scored per {d.citation}
          </InfoNote>
        </div>
      </div>
    </div>
  );
}
