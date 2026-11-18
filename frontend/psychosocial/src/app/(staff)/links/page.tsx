'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { Ban, CheckCircle2, ChevronLeft, ChevronRight, Clock, Hourglass, ListChecks, Loader2, Lock, Send } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/format';
import type { SentLink, SentLinkStatus } from '@/lib/types';
import { Badge, type BadgeTone, Button, PageHeader, SegmentGroup, SegmentTab } from '@/components/ui/brand';
import { useCan } from '@/components/staff/session-context';
import { EmptyState, NoAccess } from '@/components/screening/indicators';

type Filter = 'all' | SentLinkStatus;

const FILTERS: { key: Filter; label: string; icon: React.ElementType }[] = [
  { key: 'all', label: 'All', icon: ListChecks },
  { key: 'pending', label: 'Pending', icon: Hourglass },
  { key: 'completed', label: 'Completed', icon: CheckCircle2 },
  { key: 'expired', label: 'Expired', icon: Clock },
  { key: 'cancelled', label: 'Cancelled', icon: Ban },
];

const STATUS: Record<SentLinkStatus, { label: string; tone: BadgeTone }> = {
  pending: { label: 'Pending', tone: 'neutral' },
  completed: { label: 'Completed', tone: 'ok' },
  expired: { label: 'Link expired', tone: 'warn' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
};

const PAGE_SIZE = 25;
const RESTRICTED = 'Clinical data restricted to treating provider.';

function Restricted() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <Lock className="h-3.5 w-3.5" aria-hidden="true" />
      {RESTRICTED}
    </span>
  );
}

/**
 * Every link the clinic sent, with its status only (founders' decision F3 =
 * enhanced 3A). Admins work from this list: they can see who has not
 * answered yet and cancel a link nobody opened. Scores, answers and flags
 * never reach this page; the API does not send them.
 */
export default function SentLinksPage() {
  const canAssign = useCan('screening.assign');
  const canView = useCan('screening.view');
  const canSeePatients = useCan('patients.view');
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>('all');
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ['sent-links', filter, page],
    enabled: canAssign,
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (filter !== 'all') params.set('status', filter);
      return api.getPage<SentLink[]>(`/psychosocial/assignments?${params}`);
    },
  });

  const cancel = useMutation({
    mutationFn: (id: string) => api.post(`/psychosocial/assignments/${id}/cancel`),
    onSuccess: () => {
      toast.success('Link cancelled. The patient can no longer open it.');
      qc.invalidateQueries({ queryKey: ['sent-links'] });
    },
    onError: (e: Error) => {
      toast.error(e.message);
      qc.invalidateQueries({ queryKey: ['sent-links'] });
    },
  });

  if (!canAssign) return <NoAccess what="sent links" />;

  const rows = query.data?.data ?? [];
  const total = query.data?.meta?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function patientCell(r: SentLink) {
    return canSeePatients ? (
      <Link href={`/patients/${r.patient_id}`} className="font-semibold text-ink hover:underline">
        {r.patient_name}
      </Link>
    ) : (
      <span className="font-semibold text-ink">{r.patient_name}</span>
    );
  }

  function action(r: SentLink) {
    if (r.can_cancel) {
      return (
        <Button
          variant="secondary"
          className="h-9"
          onClick={() => cancel.mutate(r.id)}
          disabled={cancel.isPending}
          aria-label={`Cancel link for ${r.patient_name}`}
        >
          {cancel.isPending && cancel.variables === r.id ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Cancel link
        </Button>
      );
    }
    if (r.status === 'completed') {
      return canView && canSeePatients ? (
        <Link href={`/patients/${r.patient_id}`} className="text-sm font-semibold text-grove hover:underline">
          Open results
        </Link>
      ) : (
        <Restricted />
      );
    }
    return null;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sent links"
        subtitle="Every screener link the clinic has sent and whether the patient has answered. Results are not shown here."
      />

      <SegmentGroup role="group" aria-label="Filter links">
        {FILTERS.map((f) => (
          <SegmentTab
            key={f.key}
            active={filter === f.key}
            icon={f.icon}
            onClick={() => {
              setFilter(f.key);
              setPage(1);
            }}
          >
            {f.label}
          </SegmentTab>
        ))}
      </SegmentGroup>

      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : query.isError ? (
        <EmptyState icon={Send} title="Could not load sent links" action={<Button onClick={() => query.refetch()}>Try again</Button>}>
          {query.error.message}
        </EmptyState>
      ) : rows.length === 0 ? (
        <EmptyState icon={Send} title="No links here">
          Links sent from a patient&apos;s page show here with their status.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-card">
          <table className="hidden w-full text-left text-sm md:table">
            <caption className="sr-only">Sent links</caption>
            <thead className="border-b border-line bg-canvas/60 text-xs font-semibold text-muted">
              <tr>
                <th scope="col" className="px-5 py-3">Patient</th>
                <th scope="col" className="px-5 py-3">Screeners</th>
                <th scope="col" className="px-5 py-3">Sent</th>
                <th scope="col" className="px-5 py-3">Status</th>
                <th scope="col" className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="px-5 py-3.5">{patientCell(r)}</td>
                  <td className="px-5 py-3.5 font-medium text-ink-2">{r.screeners.join(', ')}</td>
                  <td className="px-5 py-3.5 text-[13px] text-muted">
                    <span className="tabular-nums">{formatDate(r.sent_at)}</span>
                    {r.sent_by_name ? <span className="block text-xs">by {r.sent_by_name}</span> : null}
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
                    {r.status === 'pending' ? (
                      <span className="block pt-1 text-xs text-muted">Valid until {formatDate(r.expires_at)}</span>
                    ) : null}
                  </td>
                  <td className="px-5 py-3.5 text-right">{action(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <ul className="divide-y divide-line-soft md:hidden">
            {rows.map((r) => (
              <li key={r.id} className="space-y-2 px-4 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p>{patientCell(r)}</p>
                    <p className="text-xs text-muted">
                      {r.screeners.join(', ')} · sent {formatDate(r.sent_at)}
                      {r.sent_by_name ? ` by ${r.sent_by_name}` : ''}
                    </p>
                  </div>
                  <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
                </div>
                {action(r)}
              </li>
            ))}
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
