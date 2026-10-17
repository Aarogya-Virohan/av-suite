'use client';

import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Plus, Trash2, Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { invoiceFormSchema, InvoiceFormValues } from '../../../lib/schemas';
// The invoice number is assigned by the backend (per clinic, INV-0001,
// INV-0002, ...) and any number sent by the client is ignored, so the form
// has no number field. The number is shown after the invoice is created.
import { useCreateInvoice } from '../api';
import { usePatients } from '../../patients/api';
import { hasCapability } from '../../../config/permissions';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { formatMoney } from '../../../lib/money';
import { localToday } from '../../../lib/datetime';
import { cn } from '../../../lib/cn';

interface CreateInvoiceSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

const errorText = 'mt-1.5 text-xs font-medium text-danger';
const smallInput =
  'h-9 w-full rounded-lg border border-line bg-card px-2.5 text-sm text-ink placeholder:text-slate-400 focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15';

/** Number from a form value; empty or invalid counts as 0 so totals never show NaN. */
const num = (v: unknown) => {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
};
/** Round to paise to avoid float artefacts like 0.1 + 0.2. */
const paise = (n: number) => Math.round(n * 100) / 100;
const rupees = (n: number) => formatMoney(paise(n).toFixed(2));
const toNumberOrUndefined = (v: unknown) => (v === '' || v == null ? undefined : Number(v));

const emptyItem = () => ({ description: '', quantity: 1, unit_price: undefined as unknown as number, total_price: 0 });

/*
 * Fixes:
 * - Started with an invented "Physical Therapy Session Rs 1,000" line and new
 *   lines at Rs 500; lines now start empty and must be filled in.
 * - Patient default was read before patients loaded (form held '' while the
 *   dropdown showed a name) and no error was shown; now an explicit choice.
 * - Dates were UTC (yesterday before 5:30 am IST); due date can no longer be
 *   before the issue date; discount cannot exceed the subtotal.
 * - Totals were float maths and showed "NaN" when a field was cleared.
 */
export function CreateInvoiceSlideOver({ isOpen, onClose }: CreateInvoiceSlideOverProps) {
  const createInvoice = useCreateInvoice();
  const { data: patientsResponse } = usePatients(undefined, 1, 100, isOpen && hasCapability('patients.view'));
  const patients = patientsResponse?.data || [];

  const freshValues = (): InvoiceFormValues => ({
    patient_id: '',
    issue_date: localToday(),
    due_date: localToday(),
    subtotal: 0,
    discount_amount: 0,
    tax_amount: 0,
    total_amount: 0,
    notes: '',
    items: [emptyItem()],
  });

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    setError,
    formState: { errors },
  } = useForm<InvoiceFormValues>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: freshValues(),
  });

  React.useEffect(() => {
    if (isOpen) reset(freshValues());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, reset]);

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });

  const items = watch('items') || [];
  const discountAmount = num(watch('discount_amount'));
  const taxAmount = num(watch('tax_amount'));
  const issueDate = watch('issue_date');

  const lineTotal = (i: number) => paise(num(items[i]?.quantity || 1) * num(items[i]?.unit_price));
  const subtotal = paise(items.reduce((acc, _item, i) => acc + lineTotal(i), 0));
  const totalAmount = paise(Math.max(0, subtotal - discountAmount + taxAmount));

  const onSubmit = async (values: InvoiceFormValues) => {
    if (discountAmount > subtotal) {
      setError('discount_amount', { message: 'Discount cannot be more than the subtotal' });
      return;
    }
    if (values.due_date && values.due_date < values.issue_date) {
      setError('due_date', { message: 'Due date cannot be before the issue date' });
      return;
    }
    try {
      const payload: InvoiceFormValues = {
        ...values,
        discount_amount: paise(discountAmount),
        tax_amount: paise(taxAmount),
        subtotal,
        total_amount: totalAmount,
        items: values.items.map((i) => ({
          ...i,
          description: i.description.trim(),
          unit_price: paise(num(i.unit_price)),
          total_price: paise(num(i.quantity || 1) * num(i.unit_price)),
        })),
      };
      const created = await createInvoice.mutateAsync(payload);
      const number = typeof created?.invoice_number === 'string' ? created.invoice_number : null;
      toast.success(number ? `Invoice ${number} created` : 'Invoice created successfully');
      onClose();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to create invoice');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Create Invoice" subtitle="Generate invoice for patient services">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <div>
          <FieldLabel htmlFor="inv-patient">Patient *</FieldLabel>
          <select id="inv-patient" {...register('patient_id')} className={cn(inputClass, errors.patient_id && 'border-danger')}>
            <option value="">Select patient…</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name} {p.last_name} ({p.phone})
              </option>
            ))}
          </select>
          {errors.patient_id && <p className={errorText}>{errors.patient_id.message}</p>}
          <p className="mt-1.5 text-xs text-muted">The invoice number is assigned automatically when the invoice is created.</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="inv-issue">Issue Date *</FieldLabel>
            <input id="inv-issue" {...register('issue_date')} type="date" className={cn(inputClass, errors.issue_date && 'border-danger')} />
            {errors.issue_date && <p className={errorText}>{errors.issue_date.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor="inv-due">Due Date</FieldLabel>
            <input
              id="inv-due"
              {...register('due_date')}
              type="date"
              min={issueDate || undefined}
              className={cn(inputClass, errors.due_date && 'border-danger')}
            />
            {errors.due_date && <p className={errorText}>{errors.due_date.message}</p>}
          </div>
        </div>

        {/* Line items */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-line pb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-grove">Line Items</h4>
            <button
              type="button"
              onClick={() => append(emptyItem())}
              className="flex cursor-pointer items-center gap-1 text-xs font-semibold text-grove hover:text-grove-hover"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add Item</span>
            </button>
          </div>

          {fields.map((field, idx) => {
            const itemErr = errors.items?.[idx];
            return (
              <div key={field.id} className="space-y-2 rounded-xl border border-line bg-canvas p-3">
                <div className="flex items-center gap-2">
                  <input
                    {...register(`items.${idx}.description`)}
                    placeholder="Item description (e.g. Physiotherapy session)"
                    aria-label={`Item ${idx + 1} description`}
                    className={cn(smallInput, 'flex-1', itemErr?.description && 'border-danger')}
                  />
                  {fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => remove(idx)}
                      aria-label={`Remove item ${idx + 1}`}
                      className="grid h-9 w-9 cursor-pointer place-items-center rounded-lg text-danger hover:bg-danger-wash"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-muted">Qty</label>
                    <input
                      {...register(`items.${idx}.quantity`, { setValueAs: toNumberOrUndefined })}
                      type="number"
                      min={1}
                      aria-label={`Item ${idx + 1} quantity`}
                      className={cn(smallInput, itemErr?.quantity && 'border-danger')}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-muted">Unit Price (₹)</label>
                    <input
                      {...register(`items.${idx}.unit_price`, { setValueAs: toNumberOrUndefined })}
                      type="number"
                      min={0}
                      step="0.01"
                      aria-label={`Item ${idx + 1} unit price`}
                      className={cn(smallInput, itemErr?.unit_price && 'border-danger')}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] font-medium text-muted">Total</label>
                    <div className="flex h-9 items-center font-semibold tabular-nums text-ink">{rupees(lineTotal(idx))}</div>
                  </div>
                </div>
                {itemErr && (
                  <p className={errorText}>
                    {itemErr.description ? 'Add a description. ' : ''}
                    {itemErr.unit_price ? 'Enter a price. ' : ''}
                    {itemErr.quantity ? 'Quantity must be at least 1.' : ''}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Summary */}
        <div className="space-y-3 rounded-xl border border-line bg-canvas p-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted">Subtotal</span>
            <span className="font-semibold tabular-nums text-ink">{rupees(subtotal)}</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="inv-discount" className="mb-1 block text-[11px] font-medium text-muted">
                Discount (₹)
              </label>
              <input
                id="inv-discount"
                {...register('discount_amount', { setValueAs: (v) => num(v) })}
                type="number"
                min={0}
                step="0.01"
                className={cn(smallInput, errors.discount_amount && 'border-danger')}
              />
            </div>
            <div>
              <label htmlFor="inv-tax" className="mb-1 block text-[11px] font-medium text-muted">
                Tax (₹)
              </label>
              <input id="inv-tax" {...register('tax_amount', { setValueAs: (v) => num(v) })} type="number" min={0} step="0.01" className={smallInput} />
            </div>
          </div>
          {errors.discount_amount && <p className={errorText}>{errors.discount_amount.message}</p>}
          <div className="flex items-center justify-between border-t border-line pt-3 font-bold">
            <span className="text-ink">Total Payable</span>
            <span className="tabular-nums text-grove">{rupees(totalAmount)}</span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createInvoice.isPending}>
            {createInvoice.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Generate Invoice</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
