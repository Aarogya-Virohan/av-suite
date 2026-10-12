'use client';

import React, { useState } from 'react';
import { localDateTimeInputToISO, toLocalDateTimeInput } from '../../../lib/datetime';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { treatmentSessionFormSchema, TreatmentSessionFormValues } from '../../../lib/schemas';
import { SlideOver } from '../../../components/ui/SlideOver';
import { Plus, Calendar, Loader2 } from 'lucide-react';
import { useAuthStore } from '../../../store';
import { hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { Badge, Button, Card, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

import { useTreatments, useCreateTreatmentSession } from '../../treatments/api';

const sessionDate = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});
const errorText = 'mt-1.5 text-xs font-medium text-danger';

/*
 * Restyled to the AV Suite theme. Also fixed:
 * - Sessions are listed newest first (the API does not order them, D-012).
 * - "New Session" showed for every role; it now needs treatments.create.
 * - Save could be pressed twice and create two sessions.
 * - Dates used the browser's default format (e.g. "10/12/2026, 4:30:00 PM").
 * - Clinical notes were in the form data but had no field.
 */
export function TreatmentsTab({ patientId }: { patientId: string }) {
  usePermissionSubscription(); // Decisions.md D-013
  const canCreate = hasCapability('treatments.create');
  const { data: response, isLoading } = useTreatments(patientId);
  const sessions = [...((response?.data || []) as any[])].sort(
    (a, b) =>
      String(b.treatment_date ?? '').localeCompare(String(a.treatment_date ?? '')) ||
      String(b.created_at ?? '').localeCompare(String(a.created_at ?? '')),
  );
  const [isSlideOpen, setIsSlideOpen] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TreatmentSessionFormValues>({
    resolver: zodResolver(treatmentSessionFormSchema),
    defaultValues: {
      patient_id: patientId,
      therapist_id: useAuthStore.getState().userId ?? '',
      // Local time, not UTC (see lib/datetime.ts). Pain starts empty: the old
      // default of 5 recorded an invented score whenever the field was skipped.
      treatment_date: toLocalDateTimeInput(),
      pain_score: null,
      treatment: '',
      home_advice: '',
      notes: '',
    },
  });

  const createSession = useCreateTreatmentSession();

  const openNew = () => {
    reset({
      patient_id: patientId,
      therapist_id: useAuthStore.getState().userId ?? '',
      treatment_date: toLocalDateTimeInput(),
      pain_score: null,
      treatment: '',
      home_advice: '',
      notes: '',
    });
    setIsSlideOpen(true);
  };

  const onSubmit = (values: TreatmentSessionFormValues) => {
    if (createSession.isPending) return;
    createSession.mutate(
      {
        ...values,
        treatment_date: localDateTimeInputToISO(values.treatment_date),
        home_advice: values.home_advice?.trim() ? values.home_advice.trim() : null,
        notes: values.notes?.trim() ? values.notes.trim() : null,
      },
      {
        onSuccess: () => {
          toast.success('Treatment session saved successfully.');
          setIsSlideOpen(false);
        },
        onError: (err: any) => {
          toast.error(err?.message || 'Failed to save treatment session.');
        },
      },
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display text-base font-bold text-ink">Treatment Sessions</h3>
          <p className="text-xs text-muted">Physical therapy & rehabilitation logs</p>
        </div>
        {canCreate && (
          <Button onClick={openNew}>
            <Plus className="h-4 w-4" />
            <span>New Session</span>
          </Button>
        )}
      </div>

      {isLoading ? (
        <Card className="flex items-center justify-center gap-2 p-8 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin text-grove" /> Loading sessions...
        </Card>
      ) : sessions.length === 0 ? (
        <Card className="p-8 text-center text-sm text-muted">No treatment sessions logged yet for this patient.</Card>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <Card key={session.id} className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3 border-b border-line-soft pb-2.5">
                <span className="flex items-center gap-2 text-xs font-semibold text-muted">
                  <Calendar className="h-4 w-4 text-logo-teal" />
                  {session.treatment_date ? sessionDate.format(new Date(session.treatment_date)) : 'Date not set'}
                </span>
                {session.pain_score != null && (
                  <Badge tone={session.pain_score >= 7 ? 'danger' : session.pain_score >= 4 ? 'warn' : 'ok'}>
                    Pain {session.pain_score}/10
                  </Badge>
                )}
              </div>

              <div>
                <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">Treatment performed</p>
                <p className="whitespace-pre-line text-sm text-ink-2">{session.treatment}</p>
              </div>

              {session.home_advice && (
                <div className="rounded-xl border border-line bg-canvas p-3">
                  <p className="mb-0.5 text-[11px] font-bold uppercase tracking-wider text-grove">Home exercise advice</p>
                  <p className="whitespace-pre-line text-xs text-ink-2">{session.home_advice}</p>
                </div>
              )}

              {session.notes && (
                <p className="whitespace-pre-line text-xs text-muted">
                  <span className="font-semibold text-ink-2">Notes: </span>
                  {session.notes}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

      <SlideOver
        isOpen={isSlideOpen}
        onClose={() => setIsSlideOpen(false)}
        title="Record Treatment Session"
        subtitle="Log physical therapy details & exercises"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel htmlFor="tx-date">Session Date & Time *</FieldLabel>
              <input id="tx-date" {...register('treatment_date')} type="datetime-local" className={cn(inputClass, errors.treatment_date && 'border-danger')} />
              {errors.treatment_date && <p className={errorText}>{errors.treatment_date.message}</p>}
            </div>
            <div>
              <FieldLabel htmlFor="tx-pain">Pain Score (0 to 10)</FieldLabel>
              <input
                id="tx-pain"
                {...register('pain_score', { setValueAs: (v) => (v === '' || v === null ? null : Number(v)) })}
                placeholder="Not recorded"
                type="number"
                min={0}
                max={10}
                className={cn(inputClass, errors.pain_score && 'border-danger')}
              />
              {errors.pain_score && <p className={errorText}>Enter a score from 0 to 10</p>}
            </div>
          </div>

          <div>
            <FieldLabel htmlFor="tx-treatment">Treatment Details *</FieldLabel>
            <textarea
              id="tx-treatment"
              {...register('treatment')}
              rows={4}
              placeholder="e.g. IFT applied for 15 mins, core strengthening..."
              className={cn(inputClass, 'h-auto py-2', errors.treatment && 'border-danger')}
            />
            {errors.treatment && <p className={errorText}>{errors.treatment.message}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="tx-advice">Home Exercise Advice</FieldLabel>
            <textarea
              id="tx-advice"
              {...register('home_advice')}
              rows={2}
              placeholder="e.g. Cat-camel stretch 2x daily..."
              className={cn(inputClass, 'h-auto py-2')}
            />
          </div>

          <div>
            <FieldLabel htmlFor="tx-notes">Clinical Notes</FieldLabel>
            <textarea id="tx-notes" {...register('notes')} rows={2} className={cn(inputClass, 'h-auto py-2')} />
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
            <Button type="button" variant="ghost" onClick={() => setIsSlideOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createSession.isPending}>
              {createSession.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Save Session</span>
            </Button>
          </div>
        </form>
      </SlideOver>
    </div>
  );
}
