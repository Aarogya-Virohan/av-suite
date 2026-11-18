import React from 'react';
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { useForm } from 'react-hook-form';
import type { PatientFormValues } from '../../lib/schemas';
import { ReferralSourceField } from './components/ReferralSourceField';

let lastValue: string | null | undefined;

function Harness({ initial }: { initial: string | null }) {
  const { control, watch } = useForm<PatientFormValues>({ defaultValues: { referral_source: initial } as PatientFormValues });
  lastValue = watch('referral_source');
  return <ReferralSourceField control={control} idPrefix="t" />;
}

describe('ReferralSourceField (C-05)', () => {
  it('opens an old free-text value as Other and keeps the text', () => {
    render(<Harness initial="Neighbour told me" />);
    expect((screen.getByLabelText('Referral Source') as HTMLSelectElement).value).toBe('__other__');
    expect((screen.getByLabelText('Other referral source') as HTMLInputElement).value).toBe('Neighbour told me');
    expect(lastValue).toBe('Neighbour told me');
  });

  it('stores a listed option as its label and Other text as typed', () => {
    render(<Harness initial={null} />);
    const select = screen.getByLabelText('Referral Source');
    fireEvent.change(select, { target: { value: 'Walk-in' } });
    expect(lastValue).toBe('Walk-in');
    expect(screen.queryByLabelText('Other referral source')).toBeNull();
    fireEvent.change(select, { target: { value: '__other__' } });
    expect(lastValue).toBeNull();
    fireEvent.change(screen.getByLabelText('Other referral source'), { target: { value: 'Gym poster' } });
    expect(lastValue).toBe('Gym poster');
    fireEvent.change(select, { target: { value: '' } });
    expect(lastValue).toBeNull();
  });
});
