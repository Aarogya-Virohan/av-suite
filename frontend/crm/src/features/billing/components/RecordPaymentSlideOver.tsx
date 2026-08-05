'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { SlideOver } from '../../../components/ui/SlideOver';
import { paymentFormSchema, PaymentFormValues } from '../../../lib/schemas';
import { useRecordPayment, useInvoices } from '../api';
import { mockPatients } from '../../../mocks';

interface RecordPaymentSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

export function RecordPaymentSlideOver({ isOpen, onClose }: RecordPaymentSlideOverProps) {
  const recordPayment = useRecordPayment();
  const { data: invoices = [] } = useInvoices();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: {
      invoice_id: invoices[0]?.id || '',
      patient_id: mockPatients[0]?.id || '',
      amount: 1000,
      payment_method: 'cash',
      payment_date: new Date().toISOString().slice(0, 10),
      transaction_reference: '',
      notes: '',
    },
  });

  const onSubmit = async (values: PaymentFormValues) => {
    try {
      await recordPayment.mutateAsync(values);
      toast.success('Payment recorded successfully');
      reset();
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Failed to record payment');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Record Payment" subtitle="Log payment received for an invoice">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Target Invoice *
          </label>
          <select
            {...register('invoice_id')}
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          >
            {invoices.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.invoice_number} (Total: ₹{inv.total_amount}, Paid: ₹{inv.paid_amount})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Patient *
          </label>
          <select
            {...register('patient_id')}
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          >
            {mockPatients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name} {p.last_name} ({p.phone})
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Amount Received (₹) *
            </label>
            <input
              {...register('amount', { valueAsNumber: true })}
              type="number"
              min={1}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Payment Method *
            </label>
            <select
              {...register('payment_method')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
            >
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="card">Credit / Debit Card</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="insurance">Insurance</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Transaction Reference / UPI ID
          </label>
          <input
            {...register('transaction_reference')}
            type="text"
            placeholder="e.g. UPI/81028391029"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          />
        </div>

        <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg"
          >
            Record Payment
          </button>
        </div>
      </form>
    </SlideOver>
  );
}
