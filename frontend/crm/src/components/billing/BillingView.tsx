'use client';

import React, { useState } from 'react';
import {
  Search,
  Plus,
  CreditCard,
  Printer,
  X,
  CheckCircle,
  FileText,
  IndianRupee,
  Trash2
} from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { Invoice } from '@/types/crm';
import { RecordPaymentModal } from './RecordPaymentModal';
import { useInvoices } from '@/features/billing/hooks/useBilling';

export const BillingView: React.FC<{ onOpenInvoiceModal: () => void }> = ({
  onOpenInvoiceModal
}) => {
  const { deleteInvoice, branding } = useCRMStore();
  const { data: invoices = [], isLoading, isError } = useInvoices();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [activePayInvoice, setActivePayInvoice] = useState<Invoice | null>(null);
  const [previewInvoice, setPreviewInvoice] = useState<Invoice | null>(null);
  const [previewReceipt, setPreviewReceipt] = useState<Invoice | null>(null);

  const filteredInvoices = invoices.filter((i) => {
    const matchesSearch = i.patientName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === '' || i.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalBilled = invoices.reduce((sum, i) => sum + i.total, 0);
  const totalCollected = invoices
    .filter((i) => i.status === 'Paid')
    .reduce((sum, i) => sum + i.total, 0);
  const totalOutstanding = invoices
    .filter((i) => i.status === 'Due' || i.status === 'Partial')
    .reduce((sum, i) => sum + (i.total - i.paidAmount), 0);

  if (isLoading) {
    return <div className="p-8 text-center text-[var(--text-light)]">Loading billing data...</div>;
  }

  if (isError) {
    return <div className="p-8 text-center text-red-500">Failed to load billing data. Please try again.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Financial Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm">
          <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
            Total Billed
          </span>
          <p className="text-xl font-extrabold text-[var(--text)] mt-1">
            ₹{totalBilled.toLocaleString('en-IN')}
          </p>
          <p className="text-xs text-[var(--text-light)]">{invoices.length} total invoices</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm">
          <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
            Collected
          </span>
          <p className="text-xl font-extrabold text-emerald-600 mt-1">
            ₹{totalCollected.toLocaleString('en-IN')}
          </p>
          <p className="text-xs text-emerald-600 font-semibold">Fully paid</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm">
          <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
            Outstanding
          </span>
          <p className="text-xl font-extrabold text-red-500 mt-1">
            ₹{totalOutstanding.toLocaleString('en-IN')}
          </p>
          <p className="text-xs text-red-500 font-semibold">Pending due</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm">
          <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
            Total Invoices
          </span>
          <p className="text-xl font-extrabold text-[var(--teal)] mt-1">{invoices.length}</p>
          <p className="text-xs text-[var(--text-light)]">Issued to date</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-[var(--text-light)]" />
            <input
              type="text"
              placeholder="Search invoice by patient name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
          >
            <option value="">All Status</option>
            <option value="Paid">Paid</option>
            <option value="Partial">Partial</option>
            <option value="Due">Due</option>
          </select>
        </div>

        <button
          onClick={onOpenInvoiceModal}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-sm font-bold rounded-xl hover:opacity-90 transition-opacity shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Create Invoice
        </button>
      </div>

      {/* Invoices Table */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] bg-gray-50/50 dark:bg-gray-800/30 text-[var(--text-light)] uppercase tracking-wider font-bold">
                <th className="p-4">Invoice #</th>
                <th className="p-4">Patient</th>
                <th className="p-4">Date</th>
                <th className="p-4">Total Amount</th>
                <th className="p-4">Paid</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)] text-[var(--text)]">
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-[var(--text-light)]">
                    No invoices found.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-[var(--bg)] transition-colors">
                    <td className="p-4 font-mono font-bold text-[var(--navy)] dark:text-[var(--teal)]">
                      {inv.id}
                    </td>
                    <td className="p-4 font-bold text-sm">{inv.patientName}</td>
                    <td className="p-4">{inv.date}</td>
                    <td className="p-4 font-bold">₹{inv.total.toLocaleString('en-IN')}</td>
                    <td className="p-4 font-semibold text-emerald-600">
                      ₹{inv.paidAmount.toLocaleString('en-IN')}
                    </td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-1 text-[11px] font-bold rounded-full ${
                          inv.status === 'Paid'
                            ? 'bg-emerald-500/15 text-emerald-600'
                            : inv.status === 'Partial'
                            ? 'bg-amber-500/15 text-amber-600'
                            : 'bg-red-500/15 text-red-500'
                        }`}
                      >
                        {inv.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {inv.status !== 'Paid' && (
                          <button
                            onClick={() => setActivePayInvoice(inv)}
                            className="px-2.5 py-1 text-xs font-bold rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                          >
                            Pay
                          </button>
                        )}
                        <button
                          onClick={() => setPreviewInvoice(inv)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-[var(--border)] hover:bg-[var(--bg)]"
                        >
                          Invoice PDF
                        </button>
                        {inv.status === 'Paid' && (
                          <button
                            onClick={() => setPreviewReceipt(inv)}
                            className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-[var(--border)] text-emerald-600 hover:bg-emerald-500/10"
                          >
                            Receipt
                          </button>
                        )}
                        <button
                          onClick={() => deleteInvoice(inv.id)}
                          className="p-1 rounded text-red-500 hover:bg-red-500/10"
                          title="Move to Recycle Bin"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Record Payment Modal */}
      <RecordPaymentModal
        invoice={activePayInvoice}
        isOpen={activePayInvoice !== null}
        onClose={() => setActivePayInvoice(null)}
      />

      {/* Invoice PDF Preview Modal */}
      {previewInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 overflow-y-auto">
          <div className="bg-white text-gray-900 rounded-2xl w-full max-w-2xl p-8 shadow-2xl space-y-6 my-auto">
            <div className="flex items-center justify-between border-b pb-4 no-print">
              <h3 className="font-bold text-lg">Invoice Preview</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => window.print()}
                  className="px-4 py-2 bg-teal-600 text-white text-xs font-bold rounded-lg hover:bg-teal-700 inline-flex items-center gap-1.5"
                >
                  <Printer className="w-4 h-4" />
                  Print / Save PDF
                </button>
                <button
                  onClick={() => setPreviewInvoice(null)}
                  className="p-1.5 border rounded-lg text-gray-500 hover:text-black"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Printable Document Body */}
            <div className="space-y-6 text-xs font-sans">
              <div className="flex items-start justify-between border-b-2 border-[#0B2C5F] pb-4">
                <div>
                  <h1 className="text-xl font-extrabold text-[#0B2C5F]">{branding.clinicName}</h1>
                  <p className="text-gray-500">{branding.address}</p>
                  <p className="text-gray-500">Phone: {branding.phone}</p>
                </div>
                {branding.logoBase64 && (
                  <img src={branding.logoBase64} alt="Logo" className="h-12 rounded object-cover" />
                )}
              </div>

              <div className="flex justify-between items-center bg-gray-50 p-3 rounded-lg border">
                <div>
                  <p className="text-xs uppercase font-bold text-gray-400">INVOICE TO</p>
                  <p className="font-bold text-sm text-gray-800">{previewInvoice.patientName}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-sm">Invoice #: {previewInvoice.id}</p>
                  <p className="text-gray-500">Date: {previewInvoice.date}</p>
                </div>
              </div>

              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#0B2C5F] text-white">
                    <th className="p-3 font-bold">Description</th>
                    <th className="p-3 text-right font-bold">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y border-b">
                  <tr>
                    <td className="p-3">{previewInvoice.description}</td>
                    <td className="p-3 text-right font-semibold">
                      ₹{previewInvoice.amount.toLocaleString('en-IN')}
                    </td>
                  </tr>
                  {previewInvoice.tax > 0 && (
                    <tr>
                      <td className="p-3 text-gray-600">GST / Tax</td>
                      <td className="p-3 text-right font-semibold">
                        + ₹{previewInvoice.tax.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )}
                  {previewInvoice.discount > 0 && (
                    <tr>
                      <td className="p-3 text-emerald-600 font-semibold">Discount Applied</td>
                      <td className="p-3 text-right font-semibold text-emerald-600">
                        - ₹{previewInvoice.discount.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

              <div className="flex justify-end text-sm font-extrabold text-[#0B2C5F]">
                <div className="space-x-4 border-t pt-2">
                  <span>Total Amount Due:</span>
                  <span>₹{previewInvoice.total.toLocaleString('en-IN')}</span>
                </div>
              </div>

              <div className="pt-8 border-t flex justify-between items-end text-[10px] text-gray-400">
                <p>Thank you for trusting {branding.clinicName} with your health!</p>
                <div className="text-center border-t border-gray-400 w-36 pt-1">
                  <p className="font-bold text-gray-800">{branding.doctorName}</p>
                  <p>Authorized Signatory</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment Receipt Preview Modal */}
      {previewReceipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white text-gray-900 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3 no-print">
              <h3 className="font-bold text-base">Payment Receipt</h3>
              <button
                onClick={() => setPreviewReceipt(null)}
                className="p-1 text-gray-400 hover:text-black"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-center space-y-1">
              <p className="text-3xl font-extrabold text-emerald-600">
                ₹{previewReceipt.total.toLocaleString('en-IN')}
              </p>
              <p className="text-xs font-bold text-emerald-800">✓ PAYMENT RECEIVED IN FULL</p>
            </div>

            <div className="space-y-2 text-xs border-y py-3 font-medium text-gray-700">
              <div className="flex justify-between">
                <span className="text-gray-400">Received From:</span>
                <span className="font-bold">{previewReceipt.patientName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Invoice Reference:</span>
                <span>{previewReceipt.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Date:</span>
                <span>{previewReceipt.date}</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 no-print pt-2">
              <button
                onClick={() => window.print()}
                className="w-full py-2 bg-emerald-600 text-white text-xs font-bold rounded-lg hover:bg-emerald-700 inline-flex items-center justify-center gap-1.5"
              >
                <Printer className="w-4 h-4" />
                Print Receipt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
