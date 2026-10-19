'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { CheckCircle2, ChevronLeft, ChevronRight, ClipboardList, Clock, Flag, Hourglass, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import type { SessionStatus, WorklistRow } from '@/lib/types';
import { Button, PageHeader, SegmentGroup, SegmentTab } from '@/components/ui/brand';
import { useCan } from '@/components/staff/session-context';
import {
  EmptyState,
  FlagChips,
  NoAccess,
  SessionStatusBadge,
  SeverityIndicator,
} from '@/components/screening/indicators';

type View = 'attention' | 'in_progress' | 'pending' | 'completed';

const VIEWS: { key: View; label: string; icon: React.ElementType; status?: SessionStatus }[] = [
  { key: 'attention', label: 'Needs attention', icon: Flag },
  { key: 'in_progress', label: 'In progress', icon: Hourglass, status: 'in_progress' },
  { key: 'pending', label: 'Awaiting patient', icon: Clock, status: 'pending' },
  { key: 'completed', label: 'All completed', icon: CheckCircle2, status: 'completed' },
];

const PAGE_SIZE = 20;

function ResultCell({ row }: { row: WorklistRow }) {
  const s = row.session;
  if (s.status !== 'completed') {
    return (
      <span className="text-[13px] text-muted">
        {s.answered_count} of {s.total_items} answered
      </span>
    );
  }
  return (
    <span className="flex flex-col gap-1">
      {s.scales.map((scale) => (
        <span key={scale.scale_id} className="flex items-center gap-2">
          {s.scales.length > 1 ? <span className="w-20 text-xs text-muted">{scale.label.replace('DASS-21 ', '')}</span> : null}
          <SeverityIndicator instrumentId={s.instrument_id} scale={scale} size="sm" />
        </span>
      ))}
    </span>
  );
}

export default function SessionsPage() {
  const canView = useCan('screening.view');
  const [view, setView] = useState<View>('attention');
  const [page, setPage] = useState(1);
  const active = VIEWS.find((v) => v.key === view)!;

  const query = useQuery({
    queryKey: ['worklist', view, page],
    enabled: canView,
    queryFn: async () => {
      if (view === 'attention') {
        // Submitted flags plus unsubmitted risk answers (a patient who
        // answered PHQ-9 item 9 and closed the page). The second set is
        // worked out per row by the backend (partial_risk).
        const [flagged, open] = await Promise.all([
          api.getPage<WorklistRow[]>('/psychosocial/sessions?status=completed&flagged=true&page_size=100'),
          api.getPage<WorklistRow[]>('/psychosocial/sessions?status=in_progress&page_size=100'),
        ]);
        const data = [...open.data.filter((r) => r.session.partial_risk), ...flagged.data];
        return { data, meta: { total: data.length, page: 1, page_size: data.length || 1 } };
      }
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (active.status) params.set('status', active.status);
      return api.getPage<WorklistRow[]>(`/psychosocial/sessions?${params}`);
    },
  });

  if (!canView) return <NoAccess what="screening results" />;

  const rows = query.data?.data ?? [];
  const total = query.data?.meta?.total ?? 0;
  const pages = view === 'attention' ? 1 : Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Screenings"
        subtitle="Questionnaires you have sent and their results. Risk answers are listed first."
      />

      <SegmentGroup role="group" aria-label="Filter screenings">
        {VIEWS.map((v) => (
          <SegmentTab
            key={v.key}
            active={view === v.key}
            icon={v.icon}
            onClick={() => {
              setView(v.key);
              setPage(1);
            }}
          >
            {v.label}
          </SegmentTab>
        ))}
      </SegmentGroup>

      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : query.isError ? (
        <EmptyState icon={ClipboardList} title="Could not load screenings" action={<Button onClick={() => query.refetch()}>Try again</Button>}>
          {query.error.message}
        </EmptyState>
      ) : rows.length === 0 ? (
        <EmptyState icon={ClipboardList} title={view === 'attention' ? 'Nothing needs attention' : 'No screenings here yet'}>
          {view === 'attention'
            ? 'Screenings with a referral flag or a risk answer, submitted or not, will appear here.'
            : 'Send a screener from a patient’s page to get started.'}
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-card">
          <table className="hidden w-full text-left text-sm md:table">
            <caption className="sr-only">{active.label}</caption>
            <thead className="border-b border-line bg-canvas/60 text-xs font-semibold text-muted">
              <tr>
                <th scope="col" className="px-5 py-3">Patient</th>
                <th scope="col" className="px-5 py-3">Screener</th>
                <th scope="col" className="px-5 py-3">Status</th>
                <th scope="col" className="px-5 py-3">Result</th>
                <th scope="col" className="px-5 py-3">Flags</th>
                <th scope="col" className="px-5 py-3 text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {rows.map((row) => {
                const s = row.session;
                const risky = s.risk_item_flag || s.partial_risk;
                return (
                  <tr key={s.id} className={cn('group relative transition-colors hover:bg-canvas/70', risky && 'bg-danger-wash/40')}>
                    <td className={cn('px-5 py-3.5', risky && 'border-l-4 border-danger')}>
                      <Link href={`/sessions/${s.id}`} className="font-semibold text-ink after:absolute after:inset-0 focus:outline-none">
                        {row.patient_name}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 font-medium text-ink-2">{s.short_name}</td>
                    <td className="px-5 py-3.5">
                      <SessionStatusBadge status={s.status} linkStatus={row.assignment_effective_status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <ResultCell row={row} />
                    </td>
                    <td className="px-5 py-3.5">
                      <FlagChips referral={s.referral_flag} risk={s.risk_item_flag} partialRisk={s.partial_risk} />
                    </td>
                    <td className="px-5 py-3.5 text-right text-[13px] text-muted tabular-nums">
                      {formatDate(s.completed_at ?? s.started_at ?? s.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <ul className="divide-y divide-line-soft md:hidden">
            {rows.map((row) => {
              const s = row.session;
              const risky = s.risk_item_flag || s.partial_risk;
              return (
                <li key={s.id} className={cn(risky && 'border-l-4 border-danger bg-danger-wash/40')}>
                  <Link href={`/sessions/${s.id}`} className="block space-y-2 px-4 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-ink">{row.patient_name}</p>
                        <p className="text-xs text-muted">
                          {s.short_name} · {formatDate(s.completed_at ?? s.started_at ?? s.created_at)}
                        </p>
                      </div>
                      <SessionStatusBadge status={s.status} linkStatus={row.assignment_effective_status} />
                    </div>
                    <ResultCell row={row} />
                    <FlagChips referral={s.referral_flag} risk={s.risk_item_flag} partialRisk={s.partial_risk} />
                  </Link>
                </li>
              );
            })}
          </ul>

          {pages > 1 ? (
            <div className="flex items-center justify-between border-t border-line px-5 py-3 text-sm text-muted">
              <span>
                Page {page} of {pages}
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" className="h-9 px-3" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page">
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button variant="secondary" className="h-9 px-3" disabled={page >= pages} onClick={() => setPage((p) => p + 1)} aria-label="Next page">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
