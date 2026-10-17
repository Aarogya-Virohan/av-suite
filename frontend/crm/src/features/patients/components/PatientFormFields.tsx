'use client';

import React from 'react';
import type { FieldErrors, UseFormRegister } from 'react-hook-form';
import type { PatientFormValues } from '../../../lib/schemas';
import { FieldLabel, inputClass } from '../../../components/ui/brand';
import { localToday } from '../../../lib/datetime';
import { cn } from '../../../lib/cn';

const errorText = 'mt-1.5 text-xs font-medium text-danger';
const sectionTitle = 'border-b border-line pb-1.5 text-xs font-bold uppercase tracking-wider text-grove';

/** Fields shared by Add Patient and Edit Patient so both behave the same. */
export function PatientFormFields({
  register,
  errors,
  idPrefix,
}: {
  register: UseFormRegister<PatientFormValues>;
  errors: FieldErrors<PatientFormValues>;
  idPrefix: string;
}) {
  const id = (name: string) => `${idPrefix}-${name}`;
  return (
    <>
      <div className="space-y-4">
        <h3 className={sectionTitle}>Demographics</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor={id('first')}>First Name *</FieldLabel>
            <input id={id('first')} {...register('first_name')} type="text" placeholder="Rajesh" className={cn(inputClass, errors.first_name && 'border-danger')} />
            {errors.first_name && <p className={errorText}>{errors.first_name.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor={id('last')}>Last Name *</FieldLabel>
            <input id={id('last')} {...register('last_name')} type="text" placeholder="Kumar" className={cn(inputClass, errors.last_name && 'border-danger')} />
            {errors.last_name && <p className={errorText}>{errors.last_name.message}</p>}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor={id('dob')}>Date of Birth</FieldLabel>
            <input id={id('dob')} {...register('date_of_birth')} type="date" max={localToday()} className={inputClass} />
          </div>
          <div>
            <FieldLabel htmlFor={id('gender')}>Gender</FieldLabel>
            <select id={id('gender')} {...register('gender')} className={inputClass}>
              <option value="">Not specified</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div>
          <FieldLabel htmlFor={id('complaint')}>Chief Complaint *</FieldLabel>
          <textarea
            id={id('complaint')}
            {...register('chief_complaint')}
            rows={3}
            placeholder="e.g. Lower back pain during prolonged sitting"
            className={cn(inputClass, 'h-auto py-2', errors.chief_complaint && 'border-danger')}
          />
          {errors.chief_complaint && <p className={errorText}>{errors.chief_complaint.message}</p>}
        </div>
      </div>

      <div className="space-y-4">
        <h3 className={sectionTitle}>Contact & Source</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor={id('phone')}>Phone Number *</FieldLabel>
            <input id={id('phone')} {...register('phone')} type="tel" placeholder="10-digit mobile" className={cn(inputClass, errors.phone && 'border-danger')} />
            {errors.phone && <p className={errorText}>{errors.phone.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor={id('referral')}>Referral Source</FieldLabel>
            <input id={id('referral')} {...register('referral_source')} type="text" placeholder="e.g. Google, Doctor referral" className={inputClass} />
          </div>
        </div>
      </div>
    </>
  );
}
