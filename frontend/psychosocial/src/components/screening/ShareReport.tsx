'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Check, Copy, Eye, Loader2, MessageCircle, Plus, Share2, Trash2, X } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import type { Patient, ShareOptions, SharedReport, SharedReportCreated, ShareState } from '@/lib/types';
import { reportMessage, whatsappLink } from '@/lib/whatsapp';
import { Badge, type BadgeTone, Button, Card, FieldLabel, inputClass } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { useMe } from '@/components/staff/session-context';
import { InfoNote } from './indicators';

const EXPIRY = [7, 14, 30] as const;

type Link = { title: string; url: string };

function ShareForm({
  assignmentId,
  patientId,
  onCreated,
}: {
  assignmentId: string;
  patientId: string;
  onCreated: (c: SharedReportCreated) => void;
}) {
  const qc = useQueryClient();
  const options = useQuery({
    queryKey: ['share-options'],
    queryFn: () => api.get<ShareOptions>('/psychosocial/share-options'),
    staleTime: Infinity,
  });
  const [advice, setAdvice] = useState('');
  const [picked, setPicked] = useState<string[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [days, setDays] = useState<number>(30);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.post<SharedReportCreated>(`/psychosocial/assignments/${assignmentId}/share`, {
        advice: advice.trim() || null,
        resources: picked,
        custom_links: links.filter((l) => l.title.trim() || l.url.trim()),
        expires_in_days: days,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['shares', patientId] });
      onCreated(data);
    },
    onError: (e: Error) => setError(e.message),
  });

  if (options.isPending) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
      </div>
    );
  }
  if (options.isError) return <p role="alert" className="text-sm text-danger">{options.error.message}</p>;
  const o = options.data;
  const addChip = (chip: string) =>
    setAdvice((cur) => (cur.includes(chip) ? cur : `${cur.trim()}${cur.trim() ? '\n' : ''}${chip}`).slice(0, o.advice_max));

  return (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        create.mutate();
      }}
    >
      <InfoNote>
        Share after you have discussed the result with the patient. They will see your advice first, then a plain
        summary of their scores (for example &ldquo;Elevated indicators of low mood&rdquo;), then the resources you
        pick. Flags and band names are never shown.
      </InfoNote>

      <div>
        <FieldLabel htmlFor="advice">Add clinical advice or next steps (This will be visible to the patient)</FieldLabel>
        <textarea
          id="advice"
          rows={5}
          maxLength={o.advice_max}
          value={advice}
          onChange={(e) => setAdvice(e.target.value)}
          className={cn(inputClass, 'h-auto py-2.5 leading-relaxed')}
        />
        <div className="mt-2 flex flex-wrap gap-2" aria-label="Quick fill">
          {o.advice_chips.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => addChip(chip)}
              className="rounded-full border border-line bg-canvas px-3 py-1.5 text-xs font-medium text-ink-2 hover:border-grove/50 hover:text-grove"
            >
              <Plus className="mr-1 inline h-3 w-3" aria-hidden="true" />
              {chip}
            </button>
          ))}
        </div>
      </div>

      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-ink">Attach resources</legend>
        <div className="space-y-2">
          {o.resources.map((r) => (
            <label
              key={r.key}
              className={cn(
                'flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors',
                picked.includes(r.key) ? 'border-grove/50 bg-grove-wash/50' : 'border-line hover:bg-canvas',
              )}
            >
              <input
                type="checkbox"
                checked={picked.includes(r.key)}
                onChange={() => setPicked((cur) => (cur.includes(r.key) ? cur.filter((k) => k !== r.key) : [...cur, r.key]))}
                className="mt-0.5 h-5 w-5 shrink-0 accent-[#1c7a54]"
              />
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-ink">{r.title}</span>
                <span className="block text-xs text-muted">
                  {r.description}
                  {r.source ? ` Source: ${r.source}.` : ''}
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-ink">Your own links (optional)</legend>
        <div className="space-y-3">
          {links.map((l, i) => (
            <div key={i} className="grid gap-2 rounded-xl border border-line p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto]">
              <input
                aria-label={`Link ${i + 1} title`}
                placeholder="Title, e.g. Walking plan video"
                value={l.title}
                maxLength={80}
                onChange={(e) => setLinks((cur) => cur.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)))}
                className={inputClass}
              />
              <input
                aria-label={`Link ${i + 1} address`}
                placeholder="https://"
                inputMode="url"
                value={l.url}
                maxLength={500}
                onChange={(e) => setLinks((cur) => cur.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))}
                className={inputClass}
              />
              <Button type="button" variant="ghost" aria-label={`Remove link ${i + 1}`} onClick={() => setLinks((cur) => cur.filter((_, j) => j !== i))}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          {links.length < o.custom_links_max ? (
            <Button type="button" variant="secondary" onClick={() => setLinks((cur) => [...cur, { title: '', url: '' }])}>
              <Plus className="h-4 w-4" />
              Add a link
            </Button>
          ) : null}
        </div>
      </fieldset>

      <div>
        <FieldLabel htmlFor="share-days">Link works for</FieldLabel>
        <select id="share-days" value={days} onChange={(e) => setDays(Number(e.target.value))} className={inputClass}>
          {EXPIRY.map((d) => (
            <option key={d} value={d}>
              {d} days
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p role="alert" className="rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}
      <Button type="submit" className="w-full" disabled={create.isPending}>
        {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4" />}
        Create patient link
      </Button>
    </form>
  );
}

function ShareReady({ patient, created }: { patient: Patient | null; created: SharedReportCreated }) {
  const me = useMe();
  const [copied, setCopied] = useState(false);
  const url = typeof window === 'undefined' ? created.report_path : `${window.location.origin}${created.report_path}`;
  const message = reportMessage({
    firstName: patient?.first_name ?? 'there',
    clinicName: me.active_workspace?.name ?? 'your clinic',
    url,
    expires: formatDate(created.share.expires_at),
    birthYear: created.share.birth_year_check,
  });
  const wa = whatsappLink(patient?.phone, message);
  return (
    <div className="space-y-5">
      <p className="flex items-center gap-2 font-semibold text-grove">
        <Check className="h-5 w-5" aria-hidden="true" />
        Report link ready
      </p>
      <div>
        <FieldLabel htmlFor="report-url">Patient link</FieldLabel>
        <div className="flex gap-2">
          <input id="report-url" readOnly value={url} className={cn(inputClass, 'font-mono text-xs')} onFocus={(e) => e.currentTarget.select()} />
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
        {created.share.birth_year_check
          ? 'The page asks for the year of birth on file. After 5 wrong tries the link locks and you can share again.'
          : 'No date of birth is on file, so the link opens without a check. Add the date of birth in the CRM for extra protection.'}{' '}
        For privacy, the link is shown only now.
      </InfoNote>
    </div>
  );
}

/** "Share with patient" button and drawer for one completed screening link. */
export function ShareWithPatient({ assignmentId, patientId }: { assignmentId: string; patientId: string }) {
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState<SharedReportCreated | null>(null);
  const patient = useQuery({
    queryKey: ['patient', patientId],
    enabled: open,
    queryFn: () => api.get<Patient>(`/patients/${patientId}`),
    retry: false,
  });
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <Share2 className="h-4 w-4" />
        Share with patient
      </Button>
      <SlideOver
        isOpen={open}
        onClose={() => {
          setOpen(false);
          setCreated(null);
        }}
        title="Share with patient"
        subtitle={created ? 'Send the link now; it is not shown again.' : 'After the consultation, share your advice and helpful resources.'}
      >
        {created ? (
          <ShareReady patient={patient.data ?? null} created={created} />
        ) : (
          <ShareForm assignmentId={assignmentId} patientId={patientId} onCreated={setCreated} />
        )}
      </SlideOver>
    </>
  );
}

const STATE: Record<ShareState, { label: string; tone: BadgeTone }> = {
  active: { label: 'Active', tone: 'ok' },
  expired: { label: 'Expired', tone: 'neutral' },
  revoked: { label: 'Stopped', tone: 'neutral' },
  locked: { label: 'Locked after wrong year of birth', tone: 'warn' },
};

/** Reports shared with this patient, with opens and "Stop sharing". */
export function SharedReports({ patientId }: { patientId: string }) {
  const qc = useQueryClient();
  const shares = useQuery({
    queryKey: ['shares', patientId],
    queryFn: () => api.get<SharedReport[]>(`/patients/${patientId}/psychosocial/shares`),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api.post<SharedReport>(`/psychosocial/shares/${id}/revoke`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shares', patientId] }),
  });
  const rows = shares.data ?? [];
  if (rows.length === 0) return null;
  return (
    <Card className="overflow-hidden" role="region" aria-labelledby="shared-h">
      <div className="border-b border-line px-5 py-4">
        <h2 id="shared-h" className="font-display text-[15.5px] font-bold text-ink">
          Shared with patient
        </h2>
        <p className="text-xs text-muted">Reports you shared after a consultation.</p>
      </div>
      <ul className="divide-y divide-line-soft">
        {rows.map((r) => (
          <li key={r.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-3.5">
            <div className="min-w-0 space-y-1">
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink">
                Shared {formatDate(r.created_at)}
                {r.shared_by_name ? <span className="font-normal text-muted">by {r.shared_by_name}</span> : null}
                <Badge tone={STATE[r.state].tone}>{STATE[r.state].label}</Badge>
              </p>
              <p className="flex items-center gap-1.5 text-xs text-muted">
                <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                {r.first_opened_at ? `Opened ${r.open_count} time${r.open_count === 1 ? '' : 's'}, first on ${formatDate(r.first_opened_at)}` : 'Not opened yet'}
                {r.state === 'active' ? ` · works until ${formatDate(r.expires_at)}` : ''}
              </p>
              {r.resource_titles.length ? <p className="text-xs text-ink-2">Resources: {r.resource_titles.join(', ')}</p> : null}
            </div>
            {r.state === 'active' ? (
              <Button variant="ghost" className="h-9" onClick={() => revoke.mutate(r.id)} disabled={revoke.isPending}>
                <Trash2 className="h-4 w-4" />
                Stop sharing
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </Card>
  );
}
