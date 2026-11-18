'use client';

import React from 'react';
import { useController, type Control } from 'react-hook-form';
import type { PatientFormValues } from '../../../lib/schemas';
import { FieldLabel, inputClass } from '../../../components/ui/brand';

/*
 * Referral source is a free-text column (String(255)) in the backend. The
 * dropdown only standardises what new entries look like (founder feedback
 * C-05). Any older free-text value that is not in the list opens as "Other"
 * with the text kept, so nothing already saved is lost or hidden.
 */
export const REFERRAL_OPTIONS = [
  'Google search',
  'AI search (ChatGPT, Gemini etc.)',
  'Walk-in',
  'Friend or family',
  'Doctor referral',
  'Previous treatment',
  'Practo / Justdial / other app',
  'Social media',
] as const;

const OTHER = '__other__';

export function ReferralSourceField({ control, idPrefix }: { control: Control<PatientFormValues>; idPrefix: string }) {
  const { field } = useController({ control, name: 'referral_source' });
  const value = field.value ?? '';
  const isListed = (REFERRAL_OPTIONS as readonly string[]).includes(value);
  const [otherChosen, setOtherChosen] = React.useState(!!value && !isListed);
  const selectValue = isListed ? value : otherChosen ? OTHER : '';

  return (
    <div className="space-y-2">
      <FieldLabel htmlFor={`${idPrefix}-referral`}>Referral Source</FieldLabel>
      <select
        id={`${idPrefix}-referral`}
        value={selectValue}
        onBlur={field.onBlur}
        onChange={(e) => {
          const next = e.target.value;
          if (next === OTHER) {
            setOtherChosen(true);
            field.onChange(isListed ? null : value || null);
          } else {
            setOtherChosen(false);
            field.onChange(next || null);
          }
        }}
        className={inputClass}
      >
        <option value="">Select source…</option>
        {REFERRAL_OPTIONS.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
        <option value={OTHER}>Other</option>
      </select>
      {selectValue === OTHER && (
        <input
          id={`${idPrefix}-referral-other`}
          aria-label="Other referral source"
          value={isListed ? '' : value}
          onChange={(e) => field.onChange(e.target.value || null)}
          maxLength={255}
          type="text"
          placeholder="Where did the patient hear about us?"
          className={inputClass}
        />
      )}
    </div>
  );
}
