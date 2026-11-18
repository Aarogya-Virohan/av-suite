'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { patientFormSchema, PatientFormValues, toPatientPayload } from '../../../lib/schemas';
import { useUpdatePatient } from '../api';
import { Patient } from '../../../types/api';
import { Button } from '../../../components/ui/brand';
import { PatientFormFields } from './PatientFormFields';

interface EditPatientSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
  patient: Patient;
}

/*
 * The old form filled a missing gender with 'male' and a missing referral with
 * 'Direct Walk-in', so saving any edit wrote those invented values into the
 * record. Blanks now stay blank (null), and DOB can be cleared.
 */
const fromPatient = (patient: Patient): PatientFormValues => ({
  first_name: patient.first_name,
  last_name: patient.last_name,
  date_of_birth: patient.date_of_birth || '',
  phone: patient.phone || '',
  gender: (patient.gender as PatientFormValues['gender']) ?? null,
  chief_complaint: patient.chief_complaint || '',
  referral_source: patient.referral_source ?? null,
  status: patient.status,
});

export function EditPatientSlideOver({ isOpen, onClose, patient }: EditPatientSlideOverProps) {
  const updatePatient = useUpdatePatient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    control,
} = useForm<PatientFormValues>({
    resolver: zodResolver(patientFormSchema),
    defaultValues: fromPatient(patient),
  });

  React.useEffect(() => {
    if (isOpen) reset(fromPatient(patient));
  }, [isOpen, patient, reset]);

  const onSubmit = async (values: PatientFormValues) => {
    try {
      await updatePatient.mutateAsync({
        id: patient.id,
        values: toPatientPayload(values) as Partial<PatientFormValues>,
      });
      toast.success(`Patient ${values.first_name} ${values.last_name} updated successfully`);
      onClose();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to update patient');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Edit Patient" subtitle="Update existing patient record">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <PatientFormFields register={register} control={control} errors={errors} idPrefix="edit-patient" />
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={updatePatient.isPending}>
            {updatePatient.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Save Changes</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
