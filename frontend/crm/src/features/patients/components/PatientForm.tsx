'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { patientIntakeSchema, PatientIntakeInput } from '../schemas/patient.schema';

interface PatientFormProps {
  onSubmit: (data: PatientIntakeInput) => void;
  onCancel: () => void;
  defaultValues?: Partial<PatientIntakeInput>;
}

export const PatientForm: React.FC<PatientFormProps> = ({
  onSubmit,
  onCancel,
  defaultValues
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<PatientIntakeInput>({
    resolver: zodResolver(patientIntakeSchema),
    defaultValues: {
      full_name: defaultValues?.full_name || '',
      phone: defaultValues?.phone || '',
      age: defaultValues?.age || undefined,
      gender: defaultValues?.gender || 'male',
      chief_complaint: defaultValues?.chief_complaint || '',
      referral_source: defaultValues?.referral_source || ''
    }
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 text-xs font-semibold">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Patient Name *
          </label>
          <input
            type="text"
            {...register('full_name')}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.full_name ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
            placeholder="John Doe"
          />
          {errors.full_name && (
            <p className="text-red-500 text-[10px] mt-1">{errors.full_name.message}</p>
          )}
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Phone Number (10 digits) *
          </label>
          <input
            type="tel"
            {...register('phone')}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.phone ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
            placeholder="9999999999"
          />
          {errors.phone && (
            <p className="text-red-500 text-[10px] mt-1">{errors.phone.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Age (1-120) *
          </label>
          <input
            type="number"
            {...register('age', { valueAsNumber: true })}
            className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
              errors.age ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
            }`}
            placeholder="25"
          />
          {errors.age && (
            <p className="text-red-500 text-[10px] mt-1">{errors.age.message}</p>
          )}
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Gender *
          </label>
          <select
            {...register('gender')}
            className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)]"
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
          {errors.gender && (
            <p className="text-red-500 text-[10px] mt-1">{errors.gender.message}</p>
          )}
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
            Referral Source
          </label>
          <input
            type="text"
            {...register('referral_source')}
            className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)]"
            placeholder="Instagram, Doctor Referral"
          />
        </div>
      </div>

      <div>
        <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
          Chief Complaint / Diagnosis *
        </label>
        <textarea
          {...register('chief_complaint')}
          rows={3}
          className={`w-full px-3.5 py-2.5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none transition-colors ${
            errors.chief_complaint ? 'border-red-500' : 'border-[var(--border)] focus:border-[var(--teal)]'
          }`}
          placeholder="e.g. Acute Lower Back Pain"
        />
        {errors.chief_complaint && (
          <p className="text-red-500 text-[10px] mt-1">{errors.chief_complaint.message}</p>
        )}
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
          {isSubmitting ? 'Saving...' : 'Save Patient'}
        </button>
      </div>
    </form>
  );
};
