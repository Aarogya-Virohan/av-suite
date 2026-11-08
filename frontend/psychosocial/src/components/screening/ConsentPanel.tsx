'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Check, Copy, Loader2, MessageCircle, RotateCcw, UserX } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import type { ConsentRequest, ConsentRequestCreated, Patient, PatientConsent } from '@/lib/types';
import { reconsentMessage, whatsappLink } from '@/lib/whatsapp';
import { Badge, type BadgeTone, Button, FieldLabel, inputClass } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { useMe } from '@/components/staff/session-context';
import { InfoNote } from './indicators';

const REQUEST_STATE: Record<ConsentRequest['state'], { label: string; tone: BadgeTone }> = {
  pending: { label: 'Waiting for the patient', tone: 'active' },
  granted: { label: 'Patient opted back in', tone: 'ok' },
  declined: { label: 'Patient said no', tone: 'neutral' },
  cancelled: { label: 'Replaced by a newer link', tone: 'neutral' },
  expired: { label: 'Link expired', tone: 'warn' },
};

function ConsentLinkReady({ patient, created }: { patient: Patient; created: ConsentRequestCreated }) {
  const me = useMe();
  const [copied, setCopied] = useState(false);
  const url = typeof window === 'undefined' ? created.consent_path : `${window.location.origin}${created.consent_path}`;
  const message = reconsentMessage({
    firstName: patient.first_name,
    clinicName: me.active_workspace?.name ?? 'Your clinic',
    url,
    expires: formatDate(created.request.expires_at),
  });
  const wa = whatsappLink(patient.phone, message);
  return (
    <div className="space-y-5">
      <div>
        <FieldLabel htmlFor="consent-url">Consent link</FieldLabel>
        <div className="flex gap-2">
          <input id="consent-url" readOnly value={url} className={cn(inputClass, 'font-mono text-xs')} onFocus={(e) => e.currentTarget.select()} />
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
        The patient chooses on their own phone. Only send this if the patient has told you they may want to take
        part again. For privacy, the link is shown only now.
      </InfoNote>
    </div>
  );
}

/**
 * Shown on the patient page after a withdrawal (founders' Q7 = 7B). Staff
 * who send links can ask the patient to opt back in with a consent-only link.
 */
export function ConsentPanel({ patient, consent }: { patient: Patient; consent: PatientConsent }) {
  const qc = useQueryClient();
  const [created, setCreated] = useState<ConsentRequestCreated | null>(null);
  const ask = useMutation({
    mutationFn: () => api.post<ConsentRequestCreated>(`/patients/${patient.id}/psychosocial/consent-request`, { expires_in_days: 7 }),
    onSuccess: (data) => {
      setCreated(data);
      qc.invalidateQueries({ queryKey: ['consent', patient.id] });
    },
  });

  if (consent.status !== 'withdrawn') return null;
  const req = consent.request;
  // A link answered "yes" moves the status to granted, so here a request is
  // pending, declined, cancelled or expired.
  return (
    <section aria-labelledby="consent-h" className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <UserX className="mt-0.5 h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
          <div>
            <h2 id="consent-h" className="font-display text-[15px] font-bold text-ink">
              Consent withdrawn{consent.recorded_at ? ` on ${formatDate(consent.recorded_at)}` : ''}
            </h2>
            <p className="text-sm text-ink-2">No screeners can be sent. Past results stay on record.</p>
            {req ? (
              <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                <Badge tone={REQUEST_STATE[req.state].tone}>{REQUEST_STATE[req.state].label}</Badge>
                Consent link sent {formatDate(req.created_at)}
                {req.requested_by_name ? ` by ${req.requested_by_name}` : ''}
                {req.state === 'pending' ? `, valid until ${formatDate(req.expires_at)}` : ''}
              </p>
            ) : null}
          </div>
        </div>
        <Button variant="secondary" onClick={() => ask.mutate()} disabled={ask.isPending}>
          {ask.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
          {req?.state === 'pending' ? 'New consent link' : 'Ask to opt back in'}
        </Button>
      </div>
      {ask.isError ? (
        <p role="alert" className="mt-3 rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
          {ask.error.message}
        </p>
      ) : null}
      <SlideOver
        isOpen={created !== null}
        onClose={() => setCreated(null)}
        title="Consent link"
        subtitle={`${patient.first_name} ${patient.last_name}. Any earlier consent link has stopped working.`}
      >
        {created ? <ConsentLinkReady patient={patient} created={created} /> : null}
      </SlideOver>
    </section>
  );
}
