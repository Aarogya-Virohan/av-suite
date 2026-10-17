'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useUpdateAppointment } from '../api';
import { Loader2 } from 'lucide-react';
import { Appointment } from '../../../types/api';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { localDateTimeInputToISO, toLocalDateTimeInput } from '../../../lib/datetime';

interface RescheduleSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
  appointment: Appointment | null;
}

interface RescheduleFormValues {
  scheduled_at: string;
  duration_minutes: number;
}

export function RescheduleSlideOver({ isOpen, onClose, appointment }: RescheduleSlideOverProps) {
  const updateAppointment = useUpdateAppointment();

  const getDefaultDateTime = () => (appointment?.scheduled_at ? toLocalDateTimeInput(appointment.scheduled_at) : '');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RescheduleFormValues>({
    defaultValues: {
      scheduled_at: getDefaultDateTime(),
      duration_minutes: appointment?.duration_minutes || 30,
    },
  });

  // Reset form when appointment changes
  React.useEffect(() => {
    reset({
      scheduled_at: getDefaultDateTime(),
      duration_minutes: appointment?.duration_minutes || 30,
    });
  }, [appointment, reset]);

  const onSubmit = async (values: RescheduleFormValues) => {
    if (!appointment) return;
    try {
      // Send datetime string as ISO so backend parses it correctly
      const payload = {
        ...values,
        scheduled_at: localDateTimeInputToISO(values.scheduled_at),
      };
      await updateAppointment.mutateAsync({ id: appointment.id, data: payload });
      toast.success('Appointment rescheduled successfully');
      reset();
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Failed to reschedule appointment');
    }
  };

  if (!appointment) return null;

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Reschedule Appointment" subtitle={`Reschedule for ${appointment.patient_name || 'patient'}`}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-4">
          <div>
            <FieldLabel htmlFor="rs-time">New Date & Time *</FieldLabel>
            <input
              {...register('scheduled_at', { required: 'Date and time are required' })}
              id="rs-time"
              type="datetime-local"
              className={inputClass}
            />
            {errors.scheduled_at && <p className="mt-1.5 text-xs font-medium text-danger">{errors.scheduled_at.message}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="rs-duration">Duration (Minutes) *</FieldLabel>
            <input
              {...register('duration_minutes', { valueAsNumber: true, required: 'Duration is required', min: 15 })}
              id="rs-duration"
              type="number"
              min={15}
              step={15}
              className={inputClass}
            />
            {errors.duration_minutes && <p className="mt-1.5 text-xs font-medium text-danger">{errors.duration_minutes.message || 'Minimum 15 minutes'}</p>}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={updateAppointment.isPending}>
            {updateAppointment.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Confirm Reschedule</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
