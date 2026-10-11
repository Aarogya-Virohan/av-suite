'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { SlideOver } from '../../../components/ui/SlideOver';
import { appointmentFormSchema, AppointmentFormValues } from '../../../lib/schemas';
import { useCreateAppointment, useAppointments } from '../api';
import { usePatients } from '../../patients/api';
import { useUsers } from '../../users/api';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { localDateTimeInputToISO, toLocalDateTimeInput } from '../../../lib/datetime';
import { cn } from '../../../lib/cn';

interface AddAppointmentSlideOverProps {
  isOpen: boolean;
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
export function AddAppointmentSlideOver({ isOpen, onClose }: AddAppointmentSlideOverProps) {
  const createAppointment = useCreateAppointment();
  const { data: aptResponse } = useAppointments(undefined, undefined, 1, 100);
  const existingAppointments = aptResponse?.data || [];

  const { data: patientsResponse } = usePatients(undefined, 1, 100);
  const patients = patientsResponse?.data || [];

  const { data: usersResponse } = useUsers();
  const users = usersResponse || [];
  const therapists = users.filter((u) => u.role === 'therapist' || u.role === 'admin');

  const {
    register,
    handleSubmit,
    watch,
    reset,
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
        scheduled_at: nextQuarterHour(),
        duration_minutes: 30,
        status: 'scheduled',
        source: 'manual',
      });
    }
  }, [isOpen, reset]);

  const selectedTherapist = watch('therapist_id');
  const selectedTime = watch('scheduled_at');

  // Soft double-booking warning (client side, first 100 appointments).
  const isOverlapDetected = (() => {
    if (!selectedTherapist || !selectedTime) return false;
    const targetTime = new Date(selectedTime).getTime();
    return existingAppointments.some((apt: any) => {
      if (apt.therapist_id !== selectedTherapist || apt.status === 'cancelled' || apt.status === 'no_show') return false;
      const aptTime = new Date(apt.scheduled_at).getTime();
      const diffMinutes = Math.abs(targetTime - aptTime) / (1000 * 60);
      return diffMinutes < (apt.duration_minutes || 30);
    });
  })();

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
                {u.first_name} {u.last_name} ({u.role.replace(/_/g, ' ')})
              </option>
            ))}
          </select>
          {errors.therapist_id && <p className={errorText}>{errors.therapist_id.message}</p>}
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
