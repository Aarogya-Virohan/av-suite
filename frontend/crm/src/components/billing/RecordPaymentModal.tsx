'use client';

import React, { useState } from 'react';
import { X, CreditCard } from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { Invoice, PaymentMode } from '@/types/crm';
import { toast } from 'sonner';

interface RecordPaymentModalProps {
  invoice: Invoice | null;
  isOpen: boolean;
  onClose: () => void;
}

export const RecordPaymentModal: React.FC<RecordPaymentModalProps> = ({
  invoice,
  isOpen,
  onClose
}) => {
  const { recordPayment } = useCRMStore();

  const remainingBalance = invoice ? invoice.total - invoice.paidAmount : 0;
  const [amount, setAmount] = useState<number>(remainingBalance);
  const [mode, setMode] = useState<PaymentMode>('Cash');
  const [reference, setReference] = useState('');

  if (!isOpen || !invoice) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (amount <= 0) {
      toast.error('Please enter a valid payment amount.');
      return;
    }

    recordPayment({
      invoiceId: invoice.id,
      patientId: invoice.patientId,
      amount,
      mode,
      reference: reference.trim() || undefined,
      date: new Date().toISOString().slice(0, 10)
    });

    toast.success(`Payment of ₹${amount.toLocaleString('en-IN')} recorded successfully.`);
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card max-w-md p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[var(--foreground)]">Record Payment</h2>
              <p className="text-[11px] text-slate-400">Log patient payment against outstanding dues.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-[var(--foreground)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3.5 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1 text-xs">
          <p className="font-extrabold text-[var(--foreground)]">{invoice.patientName}</p>
          <p className="text-slate-400">
            Invoice ID: {invoice.id} • Total: ₹{invoice.total.toLocaleString('en-IN')}
          </p>
          <div className="flex justify-between pt-1 font-semibold">
            <span className="text-emerald-600">Paid: ₹{invoice.paidAmount.toLocaleString('en-IN')}</span>
            <span className="text-red-500 font-extrabold">Due: ₹{remainingBalance.toLocaleString('en-IN')}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
              Payment Amount (₹) *
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              max={remainingBalance}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm font-extrabold text-emerald-600 focus:outline-none focus:border-[var(--teal)]"
              required
            />
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
              Payment Mode *
            </label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as PaymentMode)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm font-semibold focus:outline-none focus:border-[var(--teal)]"
            >
              <option value="Cash">Cash</option>
              <option value="UPI">UPI</option>
              <option value="Card">Card</option>
              <option value="Bank Transfer">Bank Transfer</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
              Transaction Ref / Notes
            </label>
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. UPI Ref #8891203"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 border border-slate-200 dark:border-slate-800 rounded-xl text-[var(--foreground)] font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 bg-emerald-600 text-white font-bold rounded-xl hover:opacity-95 transition-all shadow-md"
            >
              Confirm Payment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
export default RecordPaymentModal;
