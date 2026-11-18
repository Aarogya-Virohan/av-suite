'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { patientFormSchema, PatientFormValues, toPatientPayload } from '../../../lib/schemas';
import { useCreatePatient } from '../api';
import { Button } from '../../../components/ui/brand';
import { PatientFormFields } from './PatientFormFields';

interface AddPatientSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

const EMPTY: PatientFormValues = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  phone: '',
  gender: null,
  chief_complaint: '',
  referral_source: null,
  status: 'active',
};

export function AddPatientSlideOver({ isOpen, onClose }: AddPatientSlideOverProps) {
  const createPatient = useCreatePatient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    control,
} = useForm<PatientFormValues>({
    resolver: zodResolver(patientFormSchema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (isOpen) reset(EMPTY);
  }, [isOpen, reset]);

  const onSubmit = async (values: PatientFormValues) => {
    try {
      await createPatient.mutateAsync(toPatientPayload(values) as PatientFormValues);
      toast.success(`Patient ${values.first_name} ${values.last_name} created successfully`);
      onClose();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to create patient');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Add New Patient" subtitle="Create a new patient record">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <PatientFormFields register={register} control={control} errors={errors} idPrefix="add-patient" />
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createPatient.isPending}>
            {createPatient.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Save Patient</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
