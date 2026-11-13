'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { SlideOver } from '../../../components/ui/SlideOver';
import { appointmentFormSchema, AppointmentFormValues } from '../../../lib/schemas';
import { useAppointmentList, useAssignableTherapists, useCreateAppointment } from '../api';
import { addDays, APPOINTMENTS_DAY_LIMIT, overlapsExisting } from '../listing';
import { usePatients } from '../../patients/api';
import { hasCapability } from '../../../config/permissions';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { localDateTimeInputToISO, localToday, toLocalDateTimeInput } from '../../../lib/datetime';
import { cn } from '../../../lib/cn';

interface AddAppointmentSlideOverProps {
  isOpen: boolean;
  /** YYYY-MM-DD picked on the Appointments page; future days default to 10:00. */
  defaultDate?: string | null;
  onClose: () => void;
}

/** Next quarter hour from now, local time. */
function nextQuarterHour(): string {
  const d = new Date();
  d.setSeconds(0, 0);
  d.setMinutes(Math.ceil((d.getMinutes() + 1) / 15) * 15);
  return toLocalDateTimeInput(d);
}

const errorText = 'mt-1.5 text-xs font-medium text-danger';

/*
 * Fixes (verified on the old drawer, browser in Asia/Kolkata):
 * - Picking 10:00 stored 10:00 UTC, shown as 3:30 pm: the datetime-local value
 *   was sent without a time zone. It is now converted to UTC ISO.
 * - The default time was UTC (10:20 pm the previous day at 03:50 IST).
 * - Patient and therapist defaults were read before the lists loaded, so the
 *   form held '' while the dropdown showed a name; submit failed, and the
 *   therapist error was never shown (nothing happened on click). Both now
 *   start on an explicit "Select ..." option and show their errors.
 * - "Appointment Type" was removed: appointments have no such column, so the
 *   value was silently dropped (L-19).
 */
export function AddAppointmentSlideOver({ isOpen, onClose, defaultDate }: AddAppointmentSlideOverProps) {
  const createAppointment = useCreateAppointment();
  const { data: patientsResponse } = usePatients(undefined, 1, 100, isOpen && hasCapability('patients.view'));
  const patients = patientsResponse?.data || [];

  // Only when the drawer is open: it is mounted on the Appointments page all
  // the time, and the old GET /users ran (and failed with 403) on every visit.
  const { data: therapists = [], isError: therapistsFailed } = useAssignableTherapists(
    isOpen && hasCapability('appointments.create'),
  );

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors },
  } = useForm<AppointmentFormValues>({
    resolver: zodResolver(appointmentFormSchema),
    defaultValues: {
      patient_id: '',
      therapist_id: '',
      appointment_type: 'consultation',
      scheduled_at: '',
      duration_minutes: 30,
      status: 'scheduled',
      source: 'manual',
    },
  });

  // Fresh default time each time the drawer opens.
  React.useEffect(() => {
    if (isOpen) {
      reset({
        patient_id: '',
        therapist_id: '',
        appointment_type: 'consultation',
        scheduled_at: defaultDate && defaultDate > localToday() ? `${defaultDate}T10:00` : nextQuarterHour(),
        duration_minutes: 30,
        status: 'scheduled',
        source: 'manual',
      });
    }
  }, [isOpen, reset, defaultDate]);

  const selectedTherapist = watch('therapist_id');
  // Own scope gets only the user; choose it so a therapist need not pick themself.
  const onlyTherapist = therapists.length === 1 ? therapists[0].id : null;
  React.useEffect(() => {
    if (isOpen && onlyTherapist && !selectedTherapist) setValue('therapist_id', onlyTherapist);
  }, [isOpen, onlyTherapist, selectedTherapist, setValue]);
  const selectedTime = watch('scheduled_at');
  const selectedDuration = watch('duration_minutes');

  // Soft double-booking warning. The chosen therapist's appointments from the
  // day before to the day after are read from the server (India days), so a
  // visit crossing midnight is caught too. It used to check the 100 oldest
  // appointments of the clinic, which missed every clash once a clinic had
  // more than 100 (D-028).
  const selectedDay = /^\d{4}-\d{2}-\d{2}T/.test(selectedTime || '') ? selectedTime.slice(0, 10) : null;
  const { data: nearbyResponse } = useAppointmentList(
    {
      start_date: selectedDay ? addDays(selectedDay, -1) : undefined,
      end_date: selectedDay ? addDays(selectedDay, 1) : undefined,
      therapist: selectedTherapist || undefined,
      order: 'asc',
      offset: 0,
      limit: APPOINTMENTS_DAY_LIMIT,
    },
    isOpen && !!selectedTherapist && !!selectedDay,
  );
  const isOverlapDetected =
    !!selectedTherapist &&
    !!selectedDay &&
    overlapsExisting(
      nearbyResponse?.data ?? [],
      selectedTherapist,
      localDateTimeInputToISO(selectedTime),
      Number(selectedDuration) || 30,
    );

  const onSubmit = async (values: AppointmentFormValues) => {
    try {
      await createAppointment.mutateAsync({ ...values, scheduled_at: localDateTimeInputToISO(values.scheduled_at) });
      toast.success('Appointment scheduled successfully');
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Failed to schedule appointment');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Book Appointment" subtitle="Schedule patient visit & provider slot">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {isOverlapDetected && (
          <div className="flex items-center gap-2 rounded-xl border border-warn/30 bg-warn-wash p-3 text-xs font-medium text-warn">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>This therapist already has an appointment near this time.</span>
          </div>
        )}

        <div>
          <FieldLabel htmlFor="apt-patient">Patient *</FieldLabel>
          <select id="apt-patient" {...register('patient_id')} className={cn(inputClass, errors.patient_id && 'border-danger')}>
            <option value="">Select patient…</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name} {p.last_name} ({p.phone})
              </option>
            ))}
          </select>
          {errors.patient_id && <p className={errorText}>{errors.patient_id.message}</p>}
        </div>

        <div>
          <FieldLabel htmlFor="apt-therapist">Therapist / Provider *</FieldLabel>
          <select id="apt-therapist" {...register('therapist_id')} className={cn(inputClass, errors.therapist_id && 'border-danger')}>
            <option value="">Select therapist…</option>
            {therapists.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.role.replace(/_/g, ' ')})
              </option>
            ))}
          </select>
          {errors.therapist_id && <p className={errorText}>{errors.therapist_id.message}</p>}
          {therapistsFailed && <p className={errorText}>Could not load therapists. Close and open the form again.</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="apt-time">Date & Time *</FieldLabel>
            <input
              id="apt-time"
              {...register('scheduled_at')}
              type="datetime-local"
              className={cn(inputClass, errors.scheduled_at && 'border-danger')}
            />
            {errors.scheduled_at && <p className={errorText}>{errors.scheduled_at.message}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="apt-duration">Duration (mins)</FieldLabel>
            <input
              id="apt-duration"
              {...register('duration_minutes', { valueAsNumber: true })}
              type="number"
              min={15}
              step={15}
              className={cn(inputClass, errors.duration_minutes && 'border-danger')}
            />
            {errors.duration_minutes && <p className={errorText}>Minimum 15 minutes</p>}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createAppointment.isPending}>
            {createAppointment.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Book Appointment</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
