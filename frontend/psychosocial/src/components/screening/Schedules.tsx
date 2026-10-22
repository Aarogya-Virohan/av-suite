'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { BellRing, ChevronRight, Loader2, Repeat, Send } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/format';
import { intervalWords, scheduleStatus } from '@/lib/schedule';
import type { DueItem, InstrumentId, Schedule } from '@/lib/types';
import { Badge, Button, Card, CardHeader } from '@/components/ui/brand';
import { EmptyState } from './indicators';

function StateBadge({ s }: { s: Schedule }) {
  if (s.state === 'due') return <Badge tone="warn">Due</Badge>;
  if (s.state === 'waiting') return <Badge tone="active">Link sent</Badge>;
  if (s.state === 'upcoming') return <Badge tone="neutral">Scheduled</Badge>;
  return <Badge tone="neutral">Paused</Badge>;
}

/** Repeat schedules on the patient page, with a one-click send for due ones. */
export function PatientSchedules({
  patientId,
  onSendDue,
}: {
  patientId: string;
  onSendDue: (instruments: InstrumentId[]) => void;
}) {
  const qc = useQueryClient();
  const schedules = useQuery({
    queryKey: ['schedules', patientId],
    queryFn: () => api.get<Schedule[]>(`/patients/${patientId}/psychosocial/schedules`),
  });
  const stop = useMutation({
    mutationFn: (id: string) => api.post(`/psychosocial/schedules/${id}/stop`),
    onSuccess: () => {
      toast.success('Repeat stopped.');
      qc.invalidateQueries({ queryKey: ['schedules', patientId] });
      qc.invalidateQueries({ queryKey: ['due'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (schedules.isPending) return null;
  if (schedules.isError) return <p className="text-sm text-danger">{schedules.error.message}</p>;
  if (schedules.data.length === 0) return null;

  const due = schedules.data.filter((s) => s.state === 'due');

  return (
    <div className="space-y-3">
      {due.length > 0 ? (
        <div
          role="status"
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-warn/30 bg-warn-wash px-5 py-4"
        >
          <p className="flex items-center gap-2 text-sm font-semibold text-ink">
            <BellRing className="h-4 w-4 text-warn" aria-hidden="true" />
            {due.map((s) => s.short_name).join(' and ')} {due.length === 1 ? 'is' : 'are'} due again
          </p>
          <Button onClick={() => onSendDue(due.map((s) => s.instrument_id))}>
            <Send className="h-4 w-4" />
            Send due screeners
          </Button>
        </div>
      ) : null}
      <Card className="p-5">
        <CardHeader title="Repeat schedule" />
        <ul className="divide-y divide-line">
          {schedules.data.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <p className="flex items-center gap-2 font-semibold text-ink">
                  <Repeat className="h-4 w-4 text-muted" aria-hidden="true" />
                  {s.short_name} <span className="font-normal text-muted">{intervalWords(s.interval_days)}</span>
                  <StateBadge s={s} />
                </p>
                <p className="mt-0.5 text-xs text-muted">
                  {scheduleStatus(s)}
                  {s.last_completed_at ? ` · last answered ${formatDate(s.last_completed_at)}` : ''}
                </p>
              </div>
              <Button
                variant="ghost"
                className="h-9"
                onClick={() => stop.mutate(s.id)}
                disabled={stop.isPending}
                aria-label={`Stop repeating ${s.short_name}`}
              >
                {stop.isPending && stop.variables === s.id ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Stop repeating
              </Button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/** Clinic-wide Due list for the Screenings page. No results, only what to send. */
export function DueList() {
  const due = useQuery({
    queryKey: ['due'],
    queryFn: () => api.get<DueItem[]>('/psychosocial/due'),
  });

  if (due.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </div>
    );
  }
  if (due.isError) {
    return (
      <EmptyState icon={BellRing} title="Could not load the Due list" action={<Button onClick={() => due.refetch()}>Try again</Button>}>
        {due.error.message}
      </EmptyState>
    );
  }
  if (due.data.length === 0) {
    return (
      <EmptyState icon={BellRing} title="Nothing is due">
        Screeners set to repeat show here when they are due again.
      </EmptyState>
    );
  }
  return (
    <ul className="overflow-hidden rounded-2xl border border-line bg-card shadow-card">
      {due.data.map((d) => (
        <li key={d.id} className="border-b border-line-soft last:border-b-0">
          <Link
            href={`/patients/${d.patient_id}`}
            className="flex items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-canvas"
          >
            <span className="min-w-0">
              <span className="block font-semibold text-ink">{d.patient_name}</span>
              <span className="block text-xs text-muted">
                {d.short_name} {intervalWords(d.interval_days)} · {scheduleStatus(d)}
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
