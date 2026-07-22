'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { appointmentSchema, AppointmentInput } from '../schemas/appointment.schema';
import { useCRMStore } from '@/lib/store';

interface AppointmentFormProps {
  onSubmit: (data: AppointmentInput) => void;
  onCancel: () => void;
}

export const AppointmentForm: React.FC<AppointmentFormProps> = ({
  onSubmit,
  onCancel
}) => {
  const { patients, therapists } = useCRMStore();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<AppointmentInput>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: {
      patient_id: patients[0]?.id || '',
      therapist_id: therapists[0]?.id || '',
      date: new Date().toISOString().slice(0, 10),
      time: '10:00',
      duration_minutes: 30,
      notes: ''
    }
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 text-xs font-semibold">
      <div>
        <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
          Select Patient *
        </label>
        <select
          {...register('patient_id')}
          className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)]"
        >
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.mobile})
            </option>
          ))}
        </select>
        {errors.patient_id && (
          <p className="text-red-500 text-[10px] mt-1">{errors.patient_id.message}</p>
        )}
      </div>

      <div>
        <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
          Assigned Therapist *
        </label>
        <select
          {...register('therapist_id')}
          className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)]"
        >
          {therapists.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.specialization})
            </option>
          ))}
        </select>
        {errors.therapist_id && (
          <p className="text-red-500 text-[10px] mt-1">{errors.therapist_id.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Date (YYYY-MM-DD) *
          </label>
          <input
            type="date"
            {...register('date')}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.date ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
          />
          {errors.date && (
            <p className="text-red-500 text-[10px] mt-1">{errors.date.message}</p>
          )}
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Time (HH:MM) *
          </label>
          <input
            type="time"
            {...register('time')}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.time ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
          />
          {errors.time && (
            <p className="text-red-500 text-[10px] mt-1">{errors.time.message}</p>
          )}
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Duration (min) *
          </label>
          <input
            type="number"
            {...register('duration_minutes', { valueAsNumber: true })}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.duration_minutes ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
          />
          {errors.duration_minutes && (
            <p className="text-red-500 text-[10px] mt-1">{errors.duration_minutes.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
          Appointment Notes
        </label>
        <textarea
          {...register('notes')}
          rows={2}
          className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] resize-none"
          placeholder="Chief complaint, progress goals..."
        />
      </div>

      <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border)]">
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2.5 text-xs font-bold rounded-xl border border-[var(--border)] text-[var(--foreground)] hover:bg-slate-50/80 dark:hover:bg-slate-800/80 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2.5 text-xs font-bold rounded-xl bg-[var(--navy)] text-white hover:opacity-95 transition-opacity"
        >
          {isSubmitting ? 'Booking...' : 'Confirm Slot'}
        </button>
      </div>
    </form>
  );
};
export default AppointmentForm;
