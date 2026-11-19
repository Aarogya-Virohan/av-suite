'use client';

import React, { useEffect } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { SlideOver } from '@/components/ui/SlideOver';
import { Badge, Button, FieldLabel, inputClass } from '@/components/ui/brand';
import { reasonField, REASON_MAX } from '@/components/forms/reason';
import { textareaClass } from '@/components/forms/ReasonActionSlideOver';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import { errorMessage, isPlatformApiError } from '@/lib/platform-api/errors';
import { ENTITLEMENT_STATUSES, type Entitlement, type ProductCatalogItem } from '@/lib/platform-api/types';
import { ACCESS_LABEL, ACCESS_TONE, accessState, dateInputToIso, ENTITLEMENT_STATUS_LABEL, isoToDateInput } from './entitlement';
import { useSetEntitlement } from './hooks';

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const schema = z
  .object({
    status: z.enum(ENTITLEMENT_STATUSES),
    valid_from: z.string().refine((v) => v === '' || DATE_PATTERN.test(v), 'Pick a valid date'),
    valid_until: z.string().refine((v) => v === '' || DATE_PATTERN.test(v), 'Pick a valid date'),
    reason: reasonField,
  })
  .refine((v) => !v.valid_from || !v.valid_until || v.valid_until > v.valid_from, {
    path: ['valid_until'],
    message: 'The end date must be after the start date',
  });
type FormValues = z.infer<typeof schema>;

/**
 * Console grant of one tool to one clinic (M-1 still open: this is the
 * console-grant model; the marketplace is not touched). Writes
 * workspace_products with source `direct` plus one audit row (0.9).
 */
export function EntitlementEditor({
  clinicId,
  clinicName,
  product,
  current,
  onClose,
}: {
  clinicId: string;
  clinicName: string;
  product: ProductCatalogItem | null;
  current: Entitlement | null;
  onClose: () => void;
}) {
  const save = useSetEntitlement(clinicId);
  const isOpen = product !== null;
  const {
    register,
    handleSubmit,
    reset,
    control,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'enabled', valid_from: '', valid_until: '', reason: '' },
  });

  useEffect(() => {
    if (!isOpen) return;
    reset({
      status: current?.status ?? 'enabled',
      valid_from: isoToDateInput(current?.valid_from ?? null),
      valid_until: isoToDateInput(current?.valid_until ?? null),
      reason: '',
    });
    save.reset();
    // Only reset when a different tool is opened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, product?.key, current, reset]);

  const [status, validFrom, validUntil] = useWatch({ control, name: ['status', 'valid_from', 'valid_until'] });
  const preview = accessState({
    status: status ?? 'enabled',
    valid_from: validFrom && DATE_PATTERN.test(validFrom) ? dateInputToIso(validFrom) : null,
    valid_until: validUntil && DATE_PATTERN.test(validUntil) ? dateInputToIso(validUntil) : null,
  });

  const onSubmit = (values: FormValues) => {
    if (!product) return;
    save.mutate(
      {
        productKey: product.key,
        body: {
          status: values.status,
          valid_from: dateInputToIso(values.valid_from),
          valid_until: dateInputToIso(values.valid_until),
          reason: values.reason,
        },
      },
      {
        onSuccess: () => {
          toast.success(`${product.name} access saved`);
          onClose();
        },
        onError: (error) => {
          if (isPlatformApiError(error) && (error.field === 'valid_from' || error.field === 'valid_until' || error.field === 'reason')) {
            setError(error.field, { message: error.message });
          }
        },
      },
    );
  };

  const serverError = save.isError && !(isPlatformApiError(save.error) && save.error.field) ? errorMessage(save.error) : null;

  return (
    <SlideOver
      isOpen={isOpen}
      onClose={save.isPending ? () => undefined : onClose}
      title={product ? `${product.name} access` : 'Tool access'}
      subtitle={clinicName}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <div className="flex items-center justify-between gap-3 rounded-xl border border-line bg-canvas p-4 text-sm">
          <span className="text-ink-2">Now</span>
          <Badge tone={ACCESS_TONE[accessState(current)]}>{ACCESS_LABEL[accessState(current)]}</Badge>
        </div>

        <fieldset>
          <legend className="mb-1.5 block text-xs font-semibold text-ink-2">Status</legend>
          <div className="grid grid-cols-2 gap-2.5">
            {ENTITLEMENT_STATUSES.map((s) => (
              <label
                key={s}
                className={cn(
                  'flex cursor-pointer items-center gap-2.5 rounded-[10px] border px-3 py-2.5 text-sm font-medium transition-colors',
                  status === s ? 'border-grove bg-grove-wash text-ink' : 'border-line bg-card text-ink-2 hover:border-slate-300',
                )}
              >
                <input type="radio" value={s} {...register('status')} className="accent-[var(--color-grove)]" />
                {ENTITLEMENT_STATUS_LABEL[s]}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="valid-from">Valid from (optional)</FieldLabel>
            <input id="valid-from" type="date" {...register('valid_from')} aria-invalid={!!errors.valid_from} className={cn(inputClass, errors.valid_from && 'border-danger')} />
            {errors.valid_from && <p className="mt-1.5 text-xs font-medium text-danger">{errors.valid_from.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor="valid-until">Valid until (optional)</FieldLabel>
            <input id="valid-until" type="date" {...register('valid_until')} aria-invalid={!!errors.valid_until} className={cn(inputClass, errors.valid_until && 'border-danger')} />
            {errors.valid_until && <p className="mt-1.5 text-xs font-medium text-danger">{errors.valid_until.message}</p>}
          </div>
        </div>
        <p className="-mt-2 text-xs text-muted">
          Dates are India time. Access starts at 00:00 on the start date and ends at 00:00 on the end date. Empty means no limit.
        </p>

        <div className="flex items-center justify-between gap-3 rounded-xl border border-line bg-card p-4 text-sm shadow-card">
          <span className="text-ink-2">After saving</span>
          <span className="flex items-center gap-2">
            <Badge tone={ACCESS_TONE[preview]}>{ACCESS_LABEL[preview]}</Badge>
            {preview === 'scheduled' && validFrom ? <span className="text-xs text-muted">from {formatDate(dateInputToIso(validFrom))}</span> : null}
          </span>
        </div>

        <div>
          <FieldLabel htmlFor="entitlement-reason">Reason (required)</FieldLabel>
          <textarea
            id="entitlement-reason"
            rows={3}
            maxLength={REASON_MAX}
            placeholder="e.g. Annual plan signed, invoice AV-2026-114"
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
          <Button type="button" variant="secondary" onClick={onClose} disabled={save.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save access
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
