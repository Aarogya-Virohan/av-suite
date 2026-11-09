'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Lock, SlidersHorizontal } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/format';
import { repeatOptionsWith } from '@/lib/schedule';
import type { ClinicSettings, InstrumentId, InstrumentSetting, ScaleThreshold } from '@/lib/types';
import { Badge, Button, Card, CardHeader, FieldLabel, inputClass, PageHeader } from '@/components/ui/brand';
import { useCan } from '@/components/staff/session-context';
import { EmptyState, InfoNote, NoAccess } from '@/components/screening/indicators';
import { ReferralContacts } from '@/components/screening/ReferralContacts';

type Defaults = Record<string, string>; // instrument id -> '' (just once) or weeks

function toDefaults(list: InstrumentSetting[]): Defaults {
  return Object.fromEntries(list.map((i) => [i.instrument_id, i.default_repeat_weeks ? String(i.default_repeat_weeks) : '']));
}

function scoreRange(min: number, max: number | null): string {
  return max == null ? `${min} and above` : min === max ? `${min}` : `${min} to ${max}`;
}

export default function SettingsPage() {
  const canConfigure = useCan('screening.configure');
  const settings = useQuery({
    queryKey: ['clinic-settings'],
    queryFn: () => api.get<ClinicSettings>('/psychosocial/settings'),
    enabled: canConfigure,
  });

  if (!canConfigure) return <NoAccess what="screening settings" />;

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Clinic-wide screening defaults. No patient data is shown here." />
      {settings.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading" />
        </div>
      ) : settings.isError ? (
        <EmptyState
          icon={SlidersHorizontal}
          title="Could not load settings"
          action={<Button onClick={() => settings.refetch()}>Try again</Button>}
        >
          {settings.error.message}
        </EmptyState>
      ) : (
        <>
          {/* Keyed on the saved data, so the form restarts from the server copy after a save. */}
          <DefaultsForm key={JSON.stringify(toDefaults(settings.data.instruments))} instruments={settings.data.instruments} />
          <ReferralContacts />
          <ReferralRules settings={settings.data} />
        </>
      )}
    </div>
  );
}

function DefaultsForm({ instruments }: { instruments: InstrumentSetting[] }) {
  const qc = useQueryClient();
  const original = useMemo(() => toDefaults(instruments), [instruments]);
  const [values, setValues] = useState<Defaults>(original);
  const changed = instruments.filter((i) => values[i.instrument_id] !== original[i.instrument_id]);

  const save = useMutation({
    mutationFn: async () => {
      // One request per changed screener, in order. Each one is audited.
      for (const inst of changed) {
        const v = values[inst.instrument_id];
        await api.put<ClinicSettings>(`/psychosocial/settings/${inst.instrument_id}`, {
          default_repeat_weeks: v ? Number(v) : null,
        });
      }
    },
    onSuccess: () => toast.success('Default repeat saved.'),
    onError: (e: Error) => toast.error(e.message),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['clinic-settings'] });
      qc.invalidateQueries({ queryKey: ['instruments'] });
    },
  });

  return (
    <Card className="p-5">
      <CardHeader title="Default repeat" />
      <p className="text-sm text-muted">
        Fills in the Repeat field when someone sends a screener. They can still change it for each patient. Changing a
        default does not change repeats that are already running.
      </p>
      <form
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <div className="grid gap-4 sm:grid-cols-3">
          {instruments.map((inst) => {
            const id = `default-${inst.instrument_id}`;
            const value = values[inst.instrument_id];
            return (
              <div key={inst.instrument_id}>
                <FieldLabel htmlFor={id}>{inst.short_name}</FieldLabel>
                <select
                  id={id}
                  className={inputClass}
                  value={value}
                  onChange={(e) => setValues((cur) => ({ ...cur, [inst.instrument_id as InstrumentId]: e.target.value }))}
                >
                  {repeatOptionsWith(value ? Number(value) : null).map((o) => (
                    <option key={o.label} value={o.weeks ?? ''}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-muted">
                  {inst.updated_at
                    ? `Changed ${formatDate(inst.updated_at)}${inst.updated_by_name ? ` by ${inst.updated_by_name}` : ''}`
                    : 'Not set yet'}
                </p>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={changed.length === 0 || save.isPending}>
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save defaults
          </Button>
          {changed.length > 0 ? (
            <Button type="button" variant="ghost" onClick={() => setValues(original)} disabled={save.isPending}>
              Undo changes
            </Button>
          ) : null}
        </div>
      </form>
    </Card>
  );
}

function ScaleTable({ scale }: { scale: ScaleThreshold }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[280px] text-sm">
        <caption className="mb-2 text-left text-xs font-semibold text-ink-2">
          {scale.label}: referral from {scale.referral_band} ({scale.referral_min_score} or more, out of {scale.max_score})
        </caption>
        <thead>
          <tr className="border-b border-line text-left text-xs text-muted">
            <th scope="col" className="py-2 pr-3 font-semibold">Band</th>
            <th scope="col" className="py-2 pr-3 font-semibold">Score</th>
            <th scope="col" className="py-2 font-semibold">Referral</th>
          </tr>
        </thead>
        <tbody>
          {scale.bands.map((b) => (
            <tr key={b.label} className="border-b border-line-soft last:border-b-0">
              <td className="py-2 pr-3 text-ink">{b.label}</td>
              <td className="py-2 pr-3 tabular-nums text-ink-2">{scoreRange(b.min_score, b.max_score)}</td>
              <td className="py-2">
                {b.refers ? <Badge tone="warn">Recommended</Badge> : <span className="text-muted">No</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReferralRules({ settings }: { settings: ClinicSettings }) {
  return (
    <Card className="p-5">
      <CardHeader
        title="Referral rules"
        action={
          settings.thresholds_editable ? null : (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-muted">
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              Fixed
            </span>
          )
        }
      />
      <InfoNote>
        These follow the published clinical norms for each questionnaire. Changing them at clinic level is not available
        yet.
      </InfoNote>
      <div className="mt-5 space-y-6">
        {settings.instruments.map((inst) => (
          <section key={inst.instrument_id} aria-labelledby={`rules-${inst.instrument_id}`} className="space-y-3">
            <h3 id={`rules-${inst.instrument_id}`} className="font-display text-[15px] font-bold text-ink">
              {inst.short_name} <span className="font-normal text-muted">· {inst.name}</span>
            </h3>
            <div className="grid gap-5 lg:grid-cols-3">
              {inst.scales.map((s) => (
                <ScaleTable key={s.scale_id} scale={s} />
              ))}
            </div>
            {inst.risk_rules.map((r) => (
              <p key={r.item_number} className="rounded-xl bg-danger-wash px-3 py-2 text-sm text-ink">
                <span className="font-semibold">Question {r.item_number}:</span> any answer from &ldquo;{r.min_label}
                &rdquo; up raises the risk flag and recommends referral, whatever the total.
              </p>
            ))}
            <p className="text-xs text-muted">Source: {inst.source}</p>
          </section>
        ))}
      </div>
    </Card>
  );
}
