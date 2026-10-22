'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Check, Copy, Loader2, MessageCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import { REPEAT_OPTIONS } from '@/lib/schedule';
import { PATIENT_TITLES, STAFF_INSTRUMENTS } from '@/lib/severity';
import type { AssignmentCreated, InstrumentId, InstrumentSummary, Patient } from '@/lib/types';
import { screenerMessage, whatsappLink } from '@/lib/whatsapp';
import { Button, FieldLabel, inputClass } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { InfoNote } from './indicators';
import { useMe } from '@/components/staff/session-context';

const EXPIRY_OPTIONS = [3, 7, 14, 30];

export function LinkReady({
  patient,
  created,
}: {
  patient: Patient;
  created: AssignmentCreated;
}) {
  const me = useMe();
  const [copied, setCopied] = useState(false);
  const url = typeof window === 'undefined' ? created.screener_path : `${window.location.origin}${created.screener_path}`;
  const minutes = created.assignment.sessions.reduce(
    (sum, s) => sum + (PATIENT_TITLES[s.instrument_id]?.minutes ?? 2),
    0,
  );
  const message = screenerMessage({
    firstName: patient.first_name,
    clinicName: me.active_workspace?.name ?? 'Your clinic',
    url,
    minutes,
    expires: formatDate(created.assignment.expires_at),
  });
  const wa = whatsappLink(patient.phone, message);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 rounded-2xl bg-grove-wash p-4 text-ok">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-grove text-white">
          <Check className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p className="font-display font-bold">Link ready</p>
          <p className="text-sm text-ink-2">
            {created.assignment.sessions.map((s) => s.short_name).join(', ')} · valid until{' '}
            {formatDate(created.assignment.expires_at)}
          </p>
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="screener-url">Patient link</FieldLabel>
        <div className="flex gap-2">
          <input id="screener-url" readOnly value={url} className={cn(inputClass, 'font-mono text-xs')} onFocus={(e) => e.currentTarget.select()} />
          <Button
            type="button"
            variant="secondary"
            className="shrink-0"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(url);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              } catch {
                /* clipboard blocked: the field is selectable */
              }
            }}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </div>

      {wa ? (
        <a
          href={wa}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-[10px] border border-grove-hover bg-gradient-to-b from-[#22895f] to-grove px-4 text-sm font-semibold text-white shadow-primary hover:from-grove hover:to-grove-hover"
        >
          <MessageCircle className="h-4 w-4" aria-hidden="true" />
          Send on WhatsApp
        </a>
      ) : (
        <InfoNote>No mobile number on file. Copy the link and send it yourself.</InfoNote>
      )}

      <details className="rounded-xl border border-line-soft bg-canvas/60 p-3 text-sm">
        <summary className="cursor-pointer font-semibold text-ink-2">Message preview</summary>
        <p className="mt-2 whitespace-pre-line text-ink-2">{message}</p>
      </details>

      <InfoNote>
        For privacy, this link is shown only now. If the patient loses it, use &ldquo;New link&rdquo; on their
        page, which also stops the old one.
      </InfoNote>
    </div>
  );
}

export function AssignDrawer({
  patient,
  open,
  onClose,
  initialSelected = [],
}: {
  patient: Patient;
  open: boolean;
  onClose: () => void;
  /** Screeners ticked when the drawer opens, e.g. the ones that are due. */
  initialSelected?: InstrumentId[];
}) {
  const [created, setCreated] = useState<AssignmentCreated | null>(null);
  return (
    <SlideOver
      isOpen={open}
      onClose={() => {
        setCreated(null);
        onClose();
      }}
      title={created ? 'Send the link' : 'Send a screener'}
      subtitle={`${patient.first_name} ${patient.last_name}`}
    >
      {/* SlideOver unmounts its children when closed, so the form starts
          fresh every time it opens. */}
      {created ? (
        <LinkReady patient={patient} created={created} />
      ) : (
        <AssignForm patient={patient} onCreated={setCreated} initialSelected={initialSelected} />
      )}
    </SlideOver>
  );
}

function AssignForm({
  patient,
  onCreated,
  initialSelected,
}: {
  patient: Patient;
  onCreated: (c: AssignmentCreated) => void;
  initialSelected: InstrumentId[];
}) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<InstrumentId[]>(initialSelected);
  const [days, setDays] = useState(7);
  // '' = just once. A select needs string values.
  const [repeat, setRepeat] = useState('');
  const [error, setError] = useState<string | null>(null);

  const instruments = useQuery({
    queryKey: ['instruments'],
    queryFn: () => api.get<InstrumentSummary[]>('/psychosocial/instruments'),
    staleTime: Infinity,
  });

  const assign = useMutation({
    mutationFn: () =>
      api.post<AssignmentCreated>(`/patients/${patient.id}/psychosocial/sessions`, {
        instruments: selected,
        expires_in_days: days,
        ...(repeat ? { repeat_every_weeks: Number(repeat) } : {}),
      }),
    onSuccess: (data) => {
      onCreated(data);
      qc.invalidateQueries({ queryKey: ['assignments', patient.id] });
      qc.invalidateQueries({ queryKey: ['schedules', patient.id] });
      qc.invalidateQueries({ queryKey: ['worklist'] });
      qc.invalidateQueries({ queryKey: ['due'] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const toggle = (id: InstrumentId) =>
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  return (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        if (selected.length === 0) {
          setError('Choose at least one questionnaire.');
          return;
        }
        assign.mutate();
      }}
    >
      {error ? (
        <p role="alert" className="rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      <fieldset>
        <legend className="mb-2 text-xs font-semibold text-ink-2">Questionnaires (the patient answers them in this order)</legend>
        {instruments.isPending ? (
          <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Loading" />
        ) : instruments.isError ? (
          <p className="text-sm text-danger">{instruments.error.message}</p>
        ) : (
          <div className="space-y-2.5">
            {instruments.data.map((inst) => {
              const on = selected.includes(inst.id);
              const order = selected.indexOf(inst.id) + 1;
              return (
                <label
                  key={inst.id}
                  className={cn(
                    'flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors focus-within:ring-2 focus-within:ring-grove/40',
                    on ? 'border-grove bg-grove-wash/60' : 'border-line bg-card hover:border-slate-300',
                  )}
                >
                  <input type="checkbox" className="sr-only" checked={on} onChange={() => toggle(inst.id)} />
                  <span
                    aria-hidden="true"
                    className={cn(
                      'mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md border-2 text-xs font-bold',
                      on ? 'border-grove bg-grove text-white' : 'border-slate-300 bg-card',
                    )}
                  >
                    {on ? order : null}
                  </span>
                  <span className="min-w-0">
                    <span className="block font-semibold text-ink">
                      {inst.short_name} <span className="font-normal text-muted">· {STAFF_INSTRUMENTS[inst.id].screensFor}</span>
                    </span>
                    <span className="block text-xs text-muted">
                      {inst.item_count} questions · about {PATIENT_TITLES[inst.id].minutes} minutes
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </fieldset>

      <div>
        <FieldLabel htmlFor="expiry">Link expires after</FieldLabel>
        <select id="expiry" className={inputClass} value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {EXPIRY_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d} days
            </option>
          ))}
        </select>
      </div>

      <div>
        <FieldLabel htmlFor="repeat">Repeat</FieldLabel>
        <select id="repeat" className={inputClass} value={repeat} onChange={(e) => setRepeat(e.target.value)}>
          {REPEAT_OPTIONS.map((o) => (
            <option key={o.label} value={o.weeks ?? ''}>
              {o.label}
            </option>
          ))}
        </select>
        <p className="mt-1.5 text-xs text-muted">
          A repeat never sends anything by itself. When it is due again, the patient shows in the Due list and you
          send the link as usual.
        </p>
      </div>

      <Button type="submit" disabled={assign.isPending} className="w-full">
        {assign.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Create link
      </Button>
    </form>
  );
}
