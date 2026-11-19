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
import { OPERATOR_ROLE_LABEL } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import { OPERATOR_ROLES, type Operator } from '@/lib/platform-api/types';
import { useUpdateOperator } from './hooks';

const ROLE_HELP = {
  owner: 'Everything in the console: tools, suspend, operators.',
  support: 'Read-only console access. No patient data, no changes.',
} as const;

export function ChangeRoleSlideOver({ operator, onClose }: { operator: Operator | null; onClose: () => void }) {
  const update = useUpdateOperator();
  const schema = z
    .object({ role: z.enum(OPERATOR_ROLES), reason: reasonField })
    .refine((v) => !operator || v.role !== operator.role, { path: ['role'], message: 'Pick a different role' });
  type FormValues = z.infer<typeof schema>;
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { role: 'support', reason: '' } });

  useEffect(() => {
    if (operator) {
      reset({ role: operator.role === 'owner' ? 'support' : 'owner', reason: '' });
      update.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operator, reset]);

  const onSubmit = (values: FormValues) => {
    if (!operator) return;
    update.mutate(
      { id: operator.id, body: { role: values.role, reason: values.reason } },
      {
        onSuccess: (o) => {
          toast.success(`${o.name} is now ${OPERATOR_ROLE_LABEL[o.role]}`);
          onClose();
        },
      },
    );
  };

  return (
    <SlideOver isOpen={operator !== null} onClose={update.isPending ? () => undefined : onClose} title="Change role" subtitle={operator?.name}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <div>
          <FieldLabel htmlFor="operator-role">New role</FieldLabel>
          <select id="operator-role" {...register('role')} className={cn(inputClass, errors.role && 'border-danger')}>
            {OPERATOR_ROLES.map((r) => (
              <option key={r} value={r}>
                {OPERATOR_ROLE_LABEL[r]}: {ROLE_HELP[r]}
              </option>
            ))}
          </select>
          {errors.role && <p className="mt-1.5 text-xs font-medium text-danger">{errors.role.message}</p>}
          <p className="mt-1.5 text-xs text-muted">Owners are Shivank, Daman and Onkar (P-7). Everyone else in tech is Support.</p>
        </div>
        <div>
          <FieldLabel htmlFor="role-reason">Reason (required)</FieldLabel>
          <textarea
            id="role-reason"
            rows={3}
            maxLength={REASON_MAX}
            aria-invalid={!!errors.reason}
            {...register('reason')}
            className={cn(textareaClass, errors.reason && 'border-danger')}
          />
          {errors.reason && <p className="mt-1.5 text-xs font-medium text-danger">{errors.reason.message}</p>}
        </div>
        {update.isError ? (
          <p role="alert" className="rounded-[10px] border border-danger/20 bg-danger-wash px-3 py-2.5 text-xs font-medium text-danger">
            {errorMessage(update.error)}
          </p>
        ) : null}
        <div className="flex justify-end gap-2.5 border-t border-line pt-5">
          <Button type="button" variant="secondary" onClick={onClose} disabled={update.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Change role
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
