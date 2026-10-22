'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { BarChart3, Download, Loader2 } from 'lucide-react';
import { api, downloadFile } from '@/lib/api';
import { cn } from '@/lib/cn';
import { barWidth, lastDays, referralLine, statsQuery } from '@/lib/stats';
import type { Aggregates, InstrumentAggregate } from '@/lib/types';
import { Button, Card, FieldLabel, inputClass, PageHeader } from '@/components/ui/brand';
import { useCan } from '@/components/staff/session-context';
import { EmptyState, InfoNote, NoAccess } from '@/components/screening/indicators';

const SCREENERS = [
  { value: '', label: 'All screeners' },
  { value: 'phq9', label: 'PHQ-9' },
  { value: 'gad7', label: 'GAD-7' },
  { value: 'dass21', label: 'DASS-21' },
];

export default function ReportsPage() {
  const allowed = useCan('screening.aggregates');
  const initial = lastDays(90);
  const [from, setFrom] = useState(initial.from);
  const [to, setTo] = useState(initial.to);
  const [instrument, setInstrument] = useState('');
  const invalid = !from || !to || from > to;
  const qs = statsQuery(from, to, instrument);

  const stats = useQuery({
    queryKey: ['aggregates', qs],
    queryFn: () => api.get<Aggregates>(`/psychosocial/aggregates?${qs}`),
    enabled: allowed && !invalid,
  });
  const exportCsv = useMutation({
    mutationFn: () =>
      downloadFile(`/psychosocial/aggregates.csv?${qs}`, `screening-statistics-${from}-to-${to}.csv`),
    onError: (e: Error) => toast.error(e.message),
  });

  if (!allowed) return <NoAccess what="clinic statistics" />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Anonymised clinic statistics for completed screeners. No patient is named or listed."
        actions={
          <Button variant="secondary" onClick={() => exportCsv.mutate()} disabled={invalid || exportCsv.isPending}>
            {exportCsv.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Export CSV
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <FieldLabel htmlFor="from">From</FieldLabel>
          <input id="from" type="date" className={inputClass} value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div>
          <FieldLabel htmlFor="to">To</FieldLabel>
          <input id="to" type="date" className={inputClass} value={to} min={from} onChange={(e) => setTo(e.target.value)} />
        </div>
        <div>
          <FieldLabel htmlFor="screener">Screener</FieldLabel>
          <select id="screener" className={inputClass} value={instrument} onChange={(e) => setInstrument(e.target.value)}>
            {SCREENERS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <InfoNote>
        To protect patients in small groups, counts from 1 to 4 are hidden, along with one more count where needed so
        a hidden number cannot be worked out. With fewer than 5 completed in the period, only the total is shown.
      </InfoNote>

      {invalid ? (
        <p role="alert" className="rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
          Choose a start date on or before the end date.
        </p>
      ) : stats.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : stats.isError ? (
        <EmptyState icon={BarChart3} title="Could not load statistics" action={<Button onClick={() => stats.refetch()}>Try again</Button>}>
          {stats.error.message}
        </EmptyState>
      ) : (
        <div className="space-y-5">
          {stats.data.instruments.map((agg) => (
            <InstrumentCard key={agg.instrument_id} agg={agg} />
          ))}
        </div>
      )}
    </div>
  );
}

function InstrumentCard({ agg }: { agg: InstrumentAggregate }) {
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-[17px] font-bold text-ink">{agg.short_name}</h2>
        <p className="text-sm text-ink-2">
          <span className="font-display text-xl font-bold tabular-nums text-ink">{agg.completed}</span> completed
        </p>
      </div>

      {agg.completed === 0 ? (
        <p className="mt-3 text-sm text-muted">None completed in this period.</p>
      ) : agg.too_few ? (
        <p className="mt-3 text-sm text-muted">Fewer than 5 completed in this period, so the breakdown is hidden.</p>
      ) : (
        <>
          <p className="mt-2 text-sm text-ink-2">
            <span className="font-semibold text-ink">Referral recommended:</span> {referralLine(agg.referral, agg.completed)}
          </p>
          <div className="mt-4 grid gap-6 lg:grid-cols-3">
            {agg.scales.map((scale) => (
              <table key={scale.scale_id} className="w-full text-sm">
                <caption className="mb-2 text-left text-xs font-semibold text-ink-2">{scale.label} by band</caption>
                <thead className="sr-only">
                  <tr>
                    <th scope="col">Band</th>
                    <th scope="col">Share</th>
                    <th scope="col">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {scale.bands.map((b) => {
                    const width = barWidth(b.count, agg.completed);
                    return (
                      <tr key={b.label}>
                        <th scope="row" className="w-[38%] py-1.5 pr-2 text-left font-normal text-ink">
                          {b.label}
                        </th>
                        <td className="py-1.5 pr-2" aria-hidden="true">
                          <div
                            className={cn(
                              'h-3 w-full rounded-sm',
                              b.suppressed ? 'border border-dashed border-line' : 'bg-line-soft',
                            )}
                            title={b.suppressed ? `${b.label}: hidden` : `${b.label}: ${b.count}`}
                          >
                            {width > 0 ? (
                              <div className="h-full rounded-r-[4px] bg-grove" style={{ width: `${width}%` }} />
                            ) : null}
                          </div>
                        </td>
                        <td className="w-14 py-1.5 text-right tabular-nums text-ink-2">
                          {b.suppressed ? <span className="text-xs text-muted">Hidden</span> : b.count}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
