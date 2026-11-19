'use client';

import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { SlideOver } from '@/components/ui/SlideOver';
import { Button, FieldLabel, inputClass } from '@/components/ui/brand';
import { reasonField, REASON_MAX } from '@/components/forms/reason';
import { textareaClass } from '@/components/forms/ReasonActionSlideOver';
import { cn } from '@/lib/cn';
import { errorMessage, isPlatformApiError } from '@/lib/platform-api/errors';
import { CLINIC_TYPES, type ClinicType } from '@/lib/platform-api/types';
import { useCreateClinic } from './hooks';

const CLINIC_TYPE_LABEL: Record<ClinicType, string> = { clinic: 'Clinic', solo: 'Solo practice', personal: 'Personal' };

const schema = z.object({
  name: z.string().trim().min(1, 'Enter the branch name').max(255, 'Keep the name under 255 characters'),
  slug: z
    .string()
    .trim()
    .min(1, 'Enter a slug')
    .max(120, 'Keep the slug under 120 characters')
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Use lowercase letters, numbers and single hyphens'),
  type: z.enum(CLINIC_TYPES),
  reason: reasonField,
});
type FormValues = z.infer<typeof schema>;

function toSlug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
}

export function AddBranchSlideOver({
  organizationId,
  organizationName,
  isOpen,
  onClose,
}: {
  organizationId: string;
  organizationName: string;
  isOpen: boolean;
  onClose: () => void;
}) {
  const create = useCreateClinic(organizationId);
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    setError,
    getFieldState,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '', slug: '', type: 'clinic', reason: '' } });

  useEffect(() => {
    if (isOpen) {
      reset({ name: '', slug: '', type: 'clinic', reason: '' });
      create.reset();
    }
    // create.reset is stable per mutation instance; only re-run on open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, reset]);

  const nameField = register('name');

  const onSubmit = (values: FormValues) => {
    create.mutate(values, {
      onSuccess: (clinic) => {
        toast.success(`Branch "${clinic.name}" added`);
        onClose();
      },
      onError: (error) => {
        if (isPlatformApiError(error) && (error.field === 'slug' || error.field === 'name' || error.field === 'reason')) {
          setError(error.field, { message: error.message });
        }
      },
    });
  };

  const serverError = create.isError && !(isPlatformApiError(create.error) && create.error.field) ? errorMessage(create.error) : null;

  return (
    <SlideOver isOpen={isOpen} onClose={create.isPending ? () => undefined : onClose} title="Add branch" subtitle={organizationName}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <p className="rounded-xl border border-line bg-canvas p-4 text-sm text-ink-2">
          The new clinic starts active with no staff and no tools. Grant tools from the clinic page. Staff are added by the clinic admin.
        </p>

        <div>
          <FieldLabel htmlFor="branch-name">Branch name</FieldLabel>
          <input
            id="branch-name"
            {...nameField}
            onChange={(e) => {
              nameField.onChange(e);
              // Suggest a slug until the operator edits it by hand.
              if (!getFieldState('slug').isDirty) setValue('slug', toSlug(e.target.value));
            }}
            placeholder="e.g. Sahaj Physio, Sector 62"
            aria-invalid={!!errors.name}
            className={cn(inputClass, errors.name && 'border-danger')}
          />
          {errors.name && <p className="mt-1.5 text-xs font-medium text-danger">{errors.name.message}</p>}
        </div>

        <div>
          <FieldLabel htmlFor="branch-slug">Slug (used in booking links)</FieldLabel>
          <input
            id="branch-slug"
            {...register('slug')}
            placeholder="sahaj-physio-sector-62"
            aria-invalid={!!errors.slug}
            className={cn(inputClass, 'font-mono text-[13px]', errors.slug && 'border-danger')}
          />
          {errors.slug && <p className="mt-1.5 text-xs font-medium text-danger">{errors.slug.message}</p>}
        </div>

        <div>
          <FieldLabel htmlFor="branch-type">Clinic type</FieldLabel>
          <select id="branch-type" {...register('type')} className={inputClass}>
            {CLINIC_TYPES.map((t) => (
              <option key={t} value={t}>
                {CLINIC_TYPE_LABEL[t]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <FieldLabel htmlFor="branch-reason">Reason (required)</FieldLabel>
          <textarea
            id="branch-reason"
            rows={3}
            maxLength={REASON_MAX}
            placeholder="e.g. New branch as per signed order form"
            aria-invalid={!!errors.reason}
            {...register('reason')}
            className={cn(textareaClass, errors.reason && 'border-danger')}
          />
          {errors.reason && <p className="mt-1.5 text-xs font-medium text-danger">{errors.reason.message}</p>}
        </div>

        {serverError ? (
          <p role="alert" className="rounded-[10px] border border-danger/20 bg-danger-wash px-3 py-2.5 text-xs font-medium text-danger">
            {serverError}
          </p>
        ) : null}

        <div className="flex justify-end gap-2.5 border-t border-line pt-5">
          <Button type="button" variant="secondary" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Add branch
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
