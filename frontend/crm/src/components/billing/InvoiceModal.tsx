'use client';

import React, { useState, useEffect } from 'react';
import { X, Receipt, Calculator, Percent } from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { toast } from 'sonner';

interface InvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InvoiceModal: React.FC<InvoiceModalProps> = ({ isOpen, onClose }) => {
  const { patients, addInvoice } = useCRMStore();

  const [patientId, setPatientId] = useState(patients[0]?.id || '');
  const [description, setDescription] = useState('Physiotherapy Consultation & Treatment Package');
  const [amount, setAmount] = useState<number>(5000);
  const [gstPct, setGstPct] = useState<number>(18);
  const [discount, setDiscount] = useState<number>(0);

  useEffect(() => {
    if (patients.length > 0 && !patientId) {
      setPatientId(patients[0].id);
    }
  }, [patients, patientId]);

  if (!isOpen) return null;

  const baseSubtotal = Math.max(0, amount);
  const discountVal = Math.max(0, Math.min(baseSubtotal, discount));
  const taxableAmount = Math.max(0, baseSubtotal - discountVal);
  const taxVal = Math.round((taxableAmount * gstPct) / 100);
  const grandTotal = Math.max(0, taxableAmount + taxVal);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const pt = patients.find((p) => p.id === patientId);
    if (!pt) {
      toast.error('Please select a patient.');
      return;
    }

    addInvoice({
      patientId: pt.id,
      patientName: pt.name,
      description: description.trim(),
      amount: baseSubtotal,
      tax: taxVal,
      discount: discountVal,
      total: grandTotal,
      date: new Date().toISOString().slice(0, 10)
    });

    toast.success(`Invoice created for ${pt.name}!`);
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card max-w-lg p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[var(--navy)]/10 text-[var(--navy)] dark:text-[#48CAE4]">
              <Receipt className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[var(--foreground)]">Create New Invoice</h2>
              <p className="text-[11px] text-slate-400">Generate a billing invoice with Tax & Discount calculations.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-[var(--foreground)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
              Select Patient *
            </label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
              required
            >
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.mobile})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
              Treatment / Service Description *
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. 10-Session Spinal Rehab Package"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                Base Amount (₹) *
              </label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-bold"
                required
              />
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                GST Rate (%)
              </label>
              <select
                value={gstPct}
                onChange={(e) => setGstPct(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
              >
                <option value={0}>0% (Exempt)</option>
                <option value={5}>5% GST</option>
                <option value={12}>12% GST</option>
                <option value={18}>18% GST</option>
                <option value={28}>28% GST</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                Discount (₹)
              </label>
              <input
                type="number"
                value={discount}
                onChange={(e) => setDiscount(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-bold text-amber-600"
              />
            </div>
          </div>

          {/* Dynamic Billing Calculation Summary Box */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-500">
              <span>Subtotal:</span>
              <span>₹{baseSubtotal.toLocaleString('en-IN')}</span>
            </div>
            {discountVal > 0 && (
              <div className="flex justify-between text-amber-600 font-medium">
                <span>Discount:</span>
                <span>- ₹{discountVal.toLocaleString('en-IN')}</span>
              </div>
            )}
            <div className="flex justify-between text-slate-500">
              <span>GST ({gstPct}%):</span>
              <span>+ ₹{taxVal.toLocaleString('en-IN')}</span>
            </div>
            <div className="flex justify-between text-sm font-extrabold text-[var(--foreground)] pt-2 border-t border-slate-200 dark:border-slate-800">
              <span>Grand Total Payable:</span>
              <span className="text-[var(--navy)] dark:text-[#48CAE4]">₹{grandTotal.toLocaleString('en-IN')}</span>
            </div>
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
              className="px-6 py-2.5 bg-[var(--navy)] text-white font-bold rounded-xl hover:opacity-95 transition-all shadow-md"
            >
              Generate Invoice
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
export default InvoiceModal;
