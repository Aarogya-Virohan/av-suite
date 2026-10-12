'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { paymentFormSchema, PaymentFormValues } from '../../../lib/schemas';
import { useRecordPayment, useInvoices } from '../api';
import { usePatients } from '../../patients/api';
import { hasCapability } from '../../../config/permissions';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { formatMoney } from '../../../lib/money';
import { localDateTimeInputToISO, localToday } from '../../../lib/datetime';
import { cn } from '../../../lib/cn';

interface RecordPaymentSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

const errorText = 'mt-1.5 text-xs font-medium text-danger';

/** Balance due in rupees, rounded to paise. API amounts are Decimal strings. */
function balanceOf(inv: { total_amount: number | string; paid_amount: number | string }) {
  return Math.round((Number(inv.total_amount || 0) - Number(inv.paid_amount || 0)) * 100) / 100;
}

/*
 * Fixes (read from the old drawer and the billing service):
 * - Invoice and patient were picked separately, so a payment could be aimed at
 *   another patient's invoice (the backend rejects it, the UI said only
 *   "Failed"). The patient now comes from the chosen invoice.
 * - Amount defaulted to an invented Rs 1,000. It now defaults to the invoice's
 *   balance due and cannot exceed it (the backend has no overpayment check, L-20).
 * - Defaults were read before data loaded and no errors were rendered, so a
 *   submit could do nothing. Fields start empty and show errors.
 * - Only invoices with a balance are offered; payment date is shown and uses
 *   the local date, not UTC; submit is disabled while saving.
 */
export function RecordPaymentSlideOver({ isOpen, onClose }: RecordPaymentSlideOverProps) {
  const recordPayment = useRecordPayment();
  const { data: invoices = [] } = useInvoices();
  const { data: patientsResponse } = usePatients(undefined, 1, 100, isOpen && hasCapability('patients.view'));
  const patients = patientsResponse?.data || [];

  const payable = invoices.filter((inv) => inv.status !== 'cancelled' && balanceOf(inv) > 0);

  const patientName = (id: string) => {
    const p = patients.find((x) => x.id === id);
    return p ? `${p.first_name} ${p.last_name}` : `Patient #${id.slice(0, 8).toUpperCase()}`;
  };

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    setError,
    formState: { errors },
  } = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: {
      invoice_id: '',
      patient_id: '',
      amount: undefined as unknown as number,
      payment_method: 'cash',
      payment_date: '',
      transaction_reference: '',
      notes: '',
    },
  });

  const today = localToday();
  React.useEffect(() => {
    if (isOpen) {
      reset({
        invoice_id: '',
        patient_id: '',
        amount: undefined as unknown as number,
        payment_method: 'cash',
        payment_date: localToday(),
        transaction_reference: '',
        notes: '',
      });
    }
  }, [isOpen, reset]);

  const invoiceId = watch('invoice_id');
  const selected = payable.find((inv) => inv.id === invoiceId) ?? null;
  const balance = selected ? balanceOf(selected) : 0;

  // Patient and default amount follow the chosen invoice.
  React.useEffect(() => {
    if (selected) {
      setValue('patient_id', selected.patient_id, { shouldValidate: true });
      setValue('amount', balance, { shouldValidate: true });
    } else {
      setValue('patient_id', '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceId]);

  const onSubmit = async (values: PaymentFormValues) => {
    if (!selected) {
      setError('invoice_id', { message: 'Select an invoice' });
      return;
    }
    if (values.amount > balance) {
      setError('amount', { message: `Cannot exceed the balance of ${formatMoney(balance.toFixed(2))}` });
      return;
    }
    // A date-only choice is sent at the current time for today, or noon local
    // otherwise, so the stored date is the day the user picked in any zone.
    const paymentDate =
      values.payment_date === today
        ? new Date().toISOString()
        : localDateTimeInputToISO(`${values.payment_date}T12:00`);
    try {
      await recordPayment.mutateAsync({ ...values, patient_id: selected.patient_id, payment_date: paymentDate });
      toast.success(`Payment of ${formatMoney(values.amount.toFixed(2))} recorded for ${selected.invoice_number}`);
      onClose();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to record payment');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Record Payment" subtitle="Log payment received for an invoice">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <FieldLabel htmlFor="pay-invoice">Invoice *</FieldLabel>
          <select id="pay-invoice" {...register('invoice_id')} className={cn(inputClass, errors.invoice_id && 'border-danger')}>
            <option value="">{payable.length ? 'Select invoice…' : 'No invoices with a balance due'}</option>
            {payable.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.invoice_number} · {patientName(inv.patient_id)} · Balance {formatMoney(balanceOf(inv).toFixed(2))}
              </option>
            ))}
          </select>
          {errors.invoice_id && <p className={errorText}>Select an invoice</p>}
        </div>

        {selected && (
          <div className="grid grid-cols-3 gap-3 rounded-xl border border-line bg-canvas p-3 text-xs">
            <div>
              <p className="text-muted">Patient</p>
              <p className="mt-0.5 font-semibold text-ink">{patientName(selected.patient_id)}</p>
            </div>
            <div>
              <p className="text-muted">Total / Paid</p>
              <p className="mt-0.5 font-semibold tabular-nums text-ink">
                {formatMoney(String(selected.total_amount))} / {formatMoney(String(selected.paid_amount))}
              </p>
            </div>
            <div>
              <p className="text-muted">Balance due</p>
              <p className="mt-0.5 font-bold tabular-nums text-danger">{formatMoney(balance.toFixed(2))}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="pay-amount">Amount Received (₹) *</FieldLabel>
            <input
              id="pay-amount"
              {...register('amount', { setValueAs: (v) => (v === '' || v == null ? undefined : Number(v)) })}
              type="number"
              min={0.01}
              step="0.01"
              max={selected ? balance : undefined}
              disabled={!selected}
              className={cn(inputClass, errors.amount && 'border-danger')}
            />
            {errors.amount && <p className={errorText}>{errors.amount.message || 'Enter an amount'}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="pay-method">Payment Method *</FieldLabel>
            <select id="pay-method" {...register('payment_method')} className={inputClass}>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="card">Credit / Debit Card</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="insurance">Insurance</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="pay-date">Payment Date *</FieldLabel>
            <input
              id="pay-date"
              {...register('payment_date')}
              type="date"
              max={today}
              className={cn(inputClass, errors.payment_date && 'border-danger')}
            />
            {errors.payment_date && <p className={errorText}>{errors.payment_date.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor="pay-ref">Transaction Reference</FieldLabel>
            <input id="pay-ref" {...register('transaction_reference')} type="text" placeholder="e.g. UPI ref no." className={inputClass} />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={recordPayment.isPending || !selected}>
            {recordPayment.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Record Payment</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
