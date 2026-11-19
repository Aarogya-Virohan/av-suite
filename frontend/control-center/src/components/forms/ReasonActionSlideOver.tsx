'use client';

import React, { useEffect } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { SlideOver } from '@/components/ui/SlideOver';
import { Button, FieldLabel } from '@/components/ui/brand';
import { cn } from '@/lib/cn';
import { reasonField, REASON_MAX } from './reason';

const schema = z.object({ reason: reasonField });
type FormValues = z.infer<typeof schema>;

export const textareaClass =
  'w-full rounded-[10px] border border-line bg-card px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15';

/**
 * Confirm an action that needs a reason (suspend, activate). The reason is
 * checked here before any request is sent; the backend checks it again.
 */
export function ReasonActionSlideOver({
  isOpen,
  onClose,
  title,
  subtitle,
  description,
  confirmLabel,
  tone = 'default',
  isPending,
  serverError,
  onConfirm,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  description: React.ReactNode;
  confirmLabel: string;
  tone?: 'default' | 'danger';
  isPending: boolean;
  serverError?: string | null;
  onConfirm: (reason: string) => void;
}) {
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { reason: '' } });

  useEffect(() => {
    if (isOpen) reset({ reason: '' });
  }, [isOpen, reset]);

  const length = useWatch({ control, name: 'reason' })?.length ?? 0;

  return (
    <SlideOver isOpen={isOpen} onClose={isPending ? () => undefined : onClose} title={title} subtitle={subtitle}>
      <form onSubmit={handleSubmit((v) => onConfirm(v.reason))} className="space-y-5" noValidate>
        <div
          className={cn(
            'flex gap-3 rounded-xl border p-4 text-sm',
            tone === 'danger' ? 'border-danger/20 bg-danger-wash text-danger' : 'border-line bg-canvas text-ink-2',
          )}
        >
          {tone === 'danger' ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> : null}
          <div>{description}</div>
        </div>

        <div>
          <FieldLabel htmlFor="action-reason">Reason (required)</FieldLabel>
          <textarea
            id="action-reason"
            rows={4}
            maxLength={REASON_MAX}
            placeholder="Why is this change being made? This is saved in the audit log."
            aria-invalid={!!errors.reason}
            {...register('reason')}
            className={cn(textareaClass, errors.reason && 'border-danger')}
          />
          <div className="mt-1.5 flex items-start justify-between gap-3">
            {errors.reason ? <p className="text-xs font-medium text-danger">{errors.reason.message}</p> : <span />}
            <span className="shrink-0 text-[11px] text-muted">
              {length}/{REASON_MAX}
            </span>
          </div>
        </div>

        {serverError ? (
          <p role="alert" className="rounded-[10px] border border-danger/20 bg-danger-wash px-3 py-2.5 text-xs font-medium text-danger">
            {serverError}
          </p>
        ) : null}

        <div className="flex justify-end gap-2.5 border-t border-line pt-5">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {confirmLabel}
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
