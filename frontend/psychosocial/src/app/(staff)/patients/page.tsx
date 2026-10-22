'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ChevronRight, Loader2, Plus, Search, Users } from 'lucide-react';
import { api } from '@/lib/api';
import { fullName } from '@/lib/format';
import type { Patient } from '@/lib/types';
import { Avatar, Button, FieldLabel, inputClass, PageHeader } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { useCan } from '@/components/staff/session-context';
import { EmptyState, NoAccess } from '@/components/screening/indicators';

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function AddPatient({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '' });
  const [error, setError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () =>
      api.post<Patient>('/patients', {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim() || null,
      }),
    onSuccess: (p) => {
      toast.success('Patient added');
      onClose();
      router.push(`/patients/${p.id}`);
    },
    onError: (e: Error) => setError(e.message),
  });
  return (
    <SlideOver isOpen={open} onClose={onClose} title="Add patient" subtitle="Name and phone are enough to send a screener.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!form.first_name.trim() || !form.last_name.trim()) {
            setError('First and last name are required.');
            return;
          }
          create.mutate();
        }}
      >
        {error ? (
          <p role="alert" className="rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
            {error}
          </p>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="p-first">First name</FieldLabel>
            <input id="p-first" className={inputClass} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} autoComplete="off" />
          </div>
          <div>
            <FieldLabel htmlFor="p-last">Last name</FieldLabel>
            <input id="p-last" className={inputClass} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} autoComplete="off" />
          </div>
        </div>
        <div>
          <FieldLabel htmlFor="p-phone">Mobile number</FieldLabel>
          <input id="p-phone" className={inputClass} inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="98765 43210" />
          <p className="mt-1.5 text-xs text-muted">Used for the WhatsApp link. Optional.</p>
        </div>
        <Button type="submit" disabled={create.isPending} className="w-full sm:w-auto">
          {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Add patient
        </Button>
      </form>
    </SlideOver>
  );
}

export default function PatientsPage() {
  const canView = useCan('patients.view');
  const canCreate = useCan('patients.create');
  const [search, setSearch] = useState('');
  const [adding, setAdding] = useState(false);
  const q = useDebounced(search.trim(), 250);

  const query = useQuery({
    queryKey: ['patients', q],
    enabled: canView,
    queryFn: () => {
      const params = new URLSearchParams({ page: '1', page_size: '50' });
      if (q) params.set('search', q);
      return api.getPage<Patient[]>(`/patients?${params}`);
    },
  });

  if (!canView) return <NoAccess what="patients" />;
  const rows = query.data?.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patients"
        subtitle="Open a patient to send a screener or review their results."
        actions={
          canCreate ? (
            <Button onClick={() => setAdding(true)}>
              <Plus className="h-4 w-4" />
              Add patient
            </Button>
          ) : null
        }
      />

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <label htmlFor="patient-search" className="sr-only">
          Search patients
        </label>
        <input
          id="patient-search"
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or phone"
          className={`${inputClass} h-11 pl-10`}
        />
      </div>

      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : query.isError ? (
        <EmptyState icon={Users} title="Could not load patients" action={<Button onClick={() => query.refetch()}>Try again</Button>}>
          {query.error.message}
        </EmptyState>
      ) : rows.length === 0 ? (
        <EmptyState icon={Users} title={q ? 'No patients match' : 'No patients yet'}>
          {q ? 'Try another name or number.' : canCreate ? 'Add your first patient to send a screener.' : 'Patients added in the clinic will appear here.'}
        </EmptyState>
      ) : (
        <ul className="divide-y divide-line-soft overflow-hidden rounded-2xl border border-line bg-card shadow-card">
          {rows.map((p) => (
            <li key={p.id}>
              <Link href={`/patients/${p.id}`} className="flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-canvas/70 sm:px-5">
                <Avatar name={fullName(p)} size={38} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-ink">{fullName(p)}</span>
                  <span className="block truncate text-xs text-muted">
                    {[p.phone, p.age ? `${p.age} yrs` : null].filter(Boolean).join(' · ') || 'No phone on file'}
                  </span>
                </span>
                <ChevronRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <AddPatient open={adding} onClose={() => setAdding(false)} />
    </div>
  );
}
