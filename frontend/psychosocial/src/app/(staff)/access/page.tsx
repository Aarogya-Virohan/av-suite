'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import type { ClinicUser, PermissionOverride } from '@/lib/types';
import { Avatar, Badge, Button, Card, PageHeader } from '@/components/ui/brand';
import { useCan, useMe } from '@/components/staff/session-context';
import { EmptyState, InfoNote, NoAccess } from '@/components/screening/indicators';

type Scope = 'none' | 'own' | 'all';

interface AccessState {
  patientsView: Scope;
  patientsCreate: Scope;
  assign: Scope;
  results: Scope; // screening.view and screening.refer move together
}

const MANAGED_KEYS = ['patients.view', 'patients.create', 'screening.assign', 'screening.view', 'screening.refer'];

function fromOverrides(list: PermissionOverride[]): AccessState {
  const get = (k: string): Scope => list.find((p) => p.capability_key === k)?.scope ?? 'none';
  return {
    patientsView: get('patients.view'),
    patientsCreate: get('patients.create'),
    assign: get('screening.assign'),
    results: get('screening.view'),
  };
}

function toOverrides(existing: PermissionOverride[], s: AccessState): PermissionOverride[] {
  // The endpoint replaces the whole override list, so keep every key this
  // page does not manage exactly as it was.
  const kept = existing.filter((p) => !MANAGED_KEYS.includes(p.capability_key));
  return [
    ...kept.map((p) => ({ capability_key: p.capability_key, scope: p.scope })),
    { capability_key: 'patients.view', scope: s.patientsView },
    { capability_key: 'patients.create', scope: s.patientsCreate },
    { capability_key: 'screening.assign', scope: s.assign },
    { capability_key: 'screening.view', scope: s.results },
    { capability_key: 'screening.refer', scope: s.results },
  ];
}

function Toggle({
  id,
  label,
  hint,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <div>
        <label htmlFor={id} className="text-sm font-semibold text-ink">
          {label}
        </label>
        <p className="text-xs text-muted">{hint}</p>
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full border transition-colors',
          checked ? 'border-grove bg-grove' : 'border-slate-300 bg-slate-200',
        )}
      >
        <span className="sr-only">{checked ? 'On' : 'Off'}</span>
        <span
          aria-hidden="true"
          className={cn('inline-block h-5 w-5 rounded-full bg-white shadow transition-transform', checked ? 'translate-x-6' : 'translate-x-1')}
        />
      </button>
    </div>
  );
}

function ResultsScope({ value, onChange, userId }: { value: Scope; onChange: (v: Scope) => void; userId: string }) {
  const opts: { v: Scope; label: string }[] = [
    { v: 'none', label: 'No access' },
    { v: 'own', label: 'Screeners they sent' },
    { v: 'all', label: 'All patients' },
  ];
  return (
    <fieldset className="py-3">
      <legend className="text-sm font-semibold text-ink">Results and referral actions</legend>
      <p className="text-xs text-muted">Individual answers and scores. Clinical staff only.</p>
      <div className="mt-2 inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
        {opts.map((o) => (
          <label
            key={o.v}
            className={cn(
              'cursor-pointer rounded-[9px] px-3 py-2 text-[13px] font-semibold transition-colors focus-within:ring-2 focus-within:ring-grove/40',
              value === o.v ? 'bg-card text-ink shadow-[0_1px_2px_rgba(20,26,51,0.08)]' : 'text-muted hover:text-ink',
            )}
          >
            <input
              type="radio"
              className="sr-only"
              name={`results-${userId}`}
              value={o.v}
              checked={value === o.v}
              onChange={() => onChange(o.v)}
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function UserAccess({ user }: { user: ClinicUser }) {
  const overrides = useQuery({
    queryKey: ['overrides', user.id],
    queryFn: () => api.get<PermissionOverride[]>(`/users/${user.id}/permissions`),
  });
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <Avatar name={user.name} size={38} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-ink">{user.name}</p>
          <p className="truncate text-xs text-muted">{user.email}</p>
        </div>
        <Badge tone={user.role === 'therapist' ? 'active' : 'neutral'}>{user.role === 'front_desk' ? 'Front desk' : 'Therapist'}</Badge>
      </div>
      {overrides.isPending ? (
        <div className="py-6">
          <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : overrides.isError ? (
        <p className="py-4 text-sm text-danger">{overrides.error.message}</p>
      ) : (
        // Keyed on the saved data, so the form starts again from the server
        // copy after every save without syncing state in an effect.
        <AccessForm key={JSON.stringify(overrides.data)} user={user} saved={overrides.data} />
      )}
    </Card>
  );
}

function AccessForm({ user, saved }: { user: ClinicUser; saved: PermissionOverride[] }) {
  const qc = useQueryClient();
  const original = useMemo(() => fromOverrides(saved), [saved]);
  const [state, setState] = useState<AccessState>(original);
  const dirty = JSON.stringify(state) !== JSON.stringify(original);

  const save = useMutation({
    mutationFn: () => api.put<PermissionOverride[]>(`/users/${user.id}/permissions`, toOverrides(saved, state)),
    onSuccess: () => {
      toast.success(`Access updated for ${user.name}`);
      qc.invalidateQueries({ queryKey: ['overrides', user.id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <>
      <div className="mt-2 divide-y divide-line-soft">
        <Toggle
          id={`pv-${user.id}`}
          label="See patients"
          hint="Needed to open a patient and send them a screener."
          checked={state.patientsView === 'all'}
          onChange={(v) => setState({ ...state, patientsView: v ? 'all' : 'none' })}
        />
        <Toggle
          id={`pc-${user.id}`}
          label="Add patients"
          hint="For clinics that do not use the CRM."
          checked={state.patientsCreate === 'all'}
          onChange={(v) => setState({ ...state, patientsCreate: v ? 'all' : 'none' })}
        />
        <Toggle
          id={`as-${user.id}`}
          label="Send screeners"
          hint="Create and cancel patient links."
          checked={state.assign === 'all'}
          onChange={(v) => setState({ ...state, assign: v ? 'all' : 'none' })}
        />
        <ResultsScope userId={user.id} value={state.results} onChange={(v) => setState({ ...state, results: v })} />
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        {dirty ? (
          <Button variant="ghost" onClick={() => setState(original)}>
            Undo
          </Button>
        ) : null}
        <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save
        </Button>
      </div>
    </>
  );
}

export default function AccessPage() {
  const canEdit = useCan('permissions.edit');
  const canList = useCan('users.view');
  const me = useMe();
  const users = useQuery({
    queryKey: ['users'],
    enabled: canEdit && canList,
    queryFn: () => api.get<ClinicUser[]>('/users'),
  });

  if (!canEdit || !canList) return <NoAccess what="access settings" />;

  const staff = (users.data ?? []).filter((u) => u.is_active && u.role !== 'admin' && u.id !== me.user.id);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Access"
        subtitle="Choose who can send screeners and who can see results. Every change is written to the audit log."
      />
      <InfoNote>
        Admins can send screeners but do not see individual results by default, as the screening policy keeps
        patient answers with the treating physiotherapist.
      </InfoNote>
      {users.isPending ? (
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      ) : users.isError ? (
        <p className="text-sm text-danger">{users.error.message}</p>
      ) : staff.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="No staff yet">
          Staff accounts are created in AV Suite user management. Add them there first.
        </EmptyState>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {staff.map((u) => (
            <UserAccess key={u.id} user={u} />
          ))}
        </div>
      )}
    </div>
  );
}
