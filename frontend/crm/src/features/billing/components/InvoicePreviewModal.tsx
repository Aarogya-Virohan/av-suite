'use client';

import React from 'react';
import { Invoice, Payment } from '../../../types/api';
import { mockPatients } from '../../../mocks';
import { Printer, X } from 'lucide-react';

interface InvoicePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  mode?: 'invoice' | 'receipt';
}

export function InvoicePreviewModal({ isOpen, onClose, invoice, mode = 'invoice' }: InvoicePreviewModalProps) {
  if (!isOpen || !invoice) return null;

  const patient = mockPatients.find((p) => p.id === invoice.patient_id);
  const patientName = patient ? `${patient.first_name} ${patient.last_name}` : invoice.patient_id;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/75 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
        {/* Header Actions */}
        <div className="flex items-center justify-between border-b pb-4 no-print">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white capitalize">
            {mode === 'invoice' ? 'Tax Invoice' : 'Payment Receipt'} — {invoice.invoice_number}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="px-3.5 py-1.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-lg flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Printer className="w-4 h-4" />
              <span>Print {mode === 'invoice' ? 'Invoice' : 'Receipt'}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-white rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Paper */}
        <div className="p-8 bg-white text-slate-900 border border-slate-200 rounded-xl space-y-6 font-sans text-xs">
          {/* Header */}
          <div className="flex items-start justify-between border-b-2 border-navy pb-4">
            <div>
              <h1 className="text-xl font-black text-[#0b2c5f] uppercase tracking-tight">
                Aarogya Virohan Health Center
              </h1>
              <p className="text-slate-500 text-[11px] mt-0.5">Sector 14, Main Road, New Delhi • +91 9876543210</p>
            </div>
            <div className="text-right">
              <span className="text-lg font-extrabold uppercase text-[#0b2c5f] block">
                {mode === 'invoice' ? 'INVOICE' : 'RECEIPT'}
              </span>
              <span className="text-slate-500 font-mono">Ref: {invoice.invoice_number}</span>
            </div>
          </div>

          {/* Patient & Billing Meta */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
            <div>
              <p className="text-[10px] font-bold uppercase text-slate-400">Billed To</p>
              <p className="text-sm font-bold text-slate-900">{patientName}</p>
              <p className="text-slate-500">{patient?.phone || '+91 9876543210'}</p>
            </div>
            <div className="text-right space-y-1">
              <p><strong className="text-slate-500">Date:</strong> {invoice.issue_date}</p>
              {invoice.due_date && <p><strong className="text-slate-500">Due Date:</strong> {invoice.due_date}</p>}
              <p>
                <strong className="text-slate-500">Status: </strong>
                <span className="uppercase font-bold text-emerald-600">{invoice.status}</span>
              </p>
            </div>
          </div>

          {/* Line Items Table */}
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100 border-b">
                <th className="p-2.5 font-bold uppercase text-[10px] text-slate-600">Description</th>
                <th className="p-2.5 font-bold uppercase text-[10px] text-slate-600 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <td className="p-2.5 font-medium">{invoice.notes || 'Clinical Consultation & Physical Therapy Sessions'}</td>
                <td className="p-2.5 text-right font-semibold">₹{invoice.subtotal.toLocaleString('en-IN')}</td>
              </tr>
              {invoice.tax_amount > 0 && (
                <tr>
                  <td className="p-2.5 text-slate-500">GST / Tax</td>
                  <td className="p-2.5 text-right text-slate-500">₹{invoice.tax_amount.toLocaleString('en-IN')}</td>
                </tr>
              )}
              {invoice.discount_amount > 0 && (
                <tr>
                  <td className="p-2.5 text-slate-500">Discount</td>
                  <td className="p-2.5 text-right text-slate-500">- ₹{invoice.discount_amount.toLocaleString('en-IN')}</td>
                </tr>
              )}
              <tr className="font-extrabold text-sm bg-slate-50 border-t-2 border-slate-200">
                <td className="p-3 text-slate-900">Total Payable Amount</td>
                <td className="p-3 text-right text-teal-700">₹{invoice.total_amount.toLocaleString('en-IN')}</td>
              </tr>
            </tbody>
          </table>

          {/* Footer Signoff */}
          <div className="pt-8 border-t flex items-end justify-between text-[11px] text-slate-400">
            <p>Computer-generated document. Thank you for visiting Aarogya Virohan Clinic.</p>
            <div className="text-center border-t border-slate-400 pt-1 w-36">
              <p className="font-bold text-slate-800">Authorized Signatory</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
