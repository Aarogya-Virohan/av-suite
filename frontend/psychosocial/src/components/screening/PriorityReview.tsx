'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, ShieldAlert } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/format';
import type { PriorityItem } from '@/lib/types';

const STATUS_WORDS: Record<PriorityItem['status'], string> = {
  completed: 'Submitted',
  in_progress: 'Answered, not submitted yet',
  cancelled: 'Answered, then the patient withdrew consent',
};

/**
 * Risk results no provider has opened yet (founders' decision F4 = 4A).
 * A row stays here until a provider opens the result. Renders nothing when
 * the list is empty, so the page stays calm on a normal day.
 */
export function PriorityReview() {
  const query = useQuery({
    queryKey: ['priority'],
    queryFn: () => api.get<PriorityItem[]>('/psychosocial/priority'),
    refetchOnMount: 'always',
    refetchInterval: 60_000,
  });

  if (query.isError) {
    return (
      <p role="alert" className="rounded-2xl border border-danger/40 bg-danger-wash px-5 py-3 text-sm text-danger">
        Could not load the priority list: {query.error.message}
      </p>
    );
  }
  const rows = query.data ?? [];
  if (rows.length === 0) return null;

  return (
    <section aria-labelledby="priority-h" className="overflow-hidden rounded-2xl border border-danger/40 bg-card shadow-card">
      <div className="flex items-start gap-3 border-b border-danger/30 bg-danger-wash px-5 py-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden="true" />
        <div>
          <h2 id="priority-h" className="font-display text-[15px] font-bold text-danger">
            Priority review ({rows.length})
          </h2>
          <p className="text-sm text-ink-2">
            Thoughts of self-harm reported. Each stays here until a provider opens the result.
          </p>
        </div>
      </div>
      <ul className="divide-y divide-line-soft">
        {rows.map((r) => (
          <li key={r.session_id}>
            <Link
              href={`/sessions/${r.session_id}`}
              className="flex items-center justify-between gap-3 border-l-4 border-danger px-5 py-3.5 transition-colors hover:bg-canvas"
            >
              <span className="min-w-0">
                <span className="block font-semibold text-ink">{r.patient_name}</span>
                <span className="block text-xs text-muted">
                  {r.short_name} · {STATUS_WORDS[r.status]} · {formatDate(r.activity_at)}
                </span>
              </span>
              <span className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-danger">
                Review <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
