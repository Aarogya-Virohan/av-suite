'use client';

import React from 'react';
import { Invoice } from '../../../types/api';
import { usePatients } from '../../patients/api';
import { useClinicSettings } from '../../settings/api';
import { useInvoicePayments } from '../api';
import { hasCapability } from '../../../config/permissions';
import { useAuthStore } from '../../../store';
import { formatMoney } from '../../../lib/money';
import { Printer, X } from 'lucide-react';
import { Badge, type BadgeTone, Button } from '../../../components/ui/brand';

interface InvoicePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  mode?: 'invoice' | 'receipt';
}

const money = (value: number | string | null | undefined) => formatMoney(value == null ? '0' : String(value));

const STATUS_TONE: Record<string, BadgeTone> = {
  paid: 'ok',
  partial: 'warn',
  unpaid: 'danger',
  overdue: 'danger',
  issued: 'info',
  draft: 'neutral',
  cancelled: 'neutral',
};

const METHOD_LABEL: Record<string, string> = {
  cash: 'Cash',
  upi: 'UPI',
  card: 'Card',
  bank_transfer: 'Bank transfer',
  insurance: 'Insurance',
  other: 'Other',
};

const dateFormat = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
function formatDate(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormat.format(date);
}

interface LineItem {
  description: string;
  quantity: number;
  unit_price: string | number;
  total_price: string | number;
}

/*
 * Every value on this document comes from the invoice, the patient or the
 * clinic settings. It previously printed a hardcoded clinic name
 * ("Aarogya Virohan Health Center"), a made-up address and phone, a fallback
 * phone number for patients without one, and an invented line item.
 * Clinic address/phone/registration are not stored yet (Decisions.md L-14),
 * so they are left out rather than invented.
 */
export function InvoicePreviewModal({ isOpen, onClose, invoice, mode = 'invoice' }: InvoicePreviewModalProps) {
  const { data: patientsResponse } = usePatients(undefined, 1, 100, isOpen && hasCapability('patients.view'));
  const patients = patientsResponse?.data || [];
  const authClinic = useAuthStore((s) => s.clinic);
  const { data: clinicSettings } = useClinicSettings(!authClinic && hasCapability('settings.view'));
  const clinic = authClinic || clinicSettings;
  const isReceipt = mode === 'receipt';
  // A receipt must say how and when the money came in (Decisions.md L-30).
  const { data: invoicePayments = [], isLoading: isLoadingPayments } = useInvoicePayments(
    invoice?.id,
    isOpen && isReceipt,
  );

  React.useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen || !invoice) return null;

  const patient = patients.find((p) => p.id === invoice.patient_id);
  // Only the first 100 patients are loaded here (Decisions.md L-8).
  const patientName = patient
    ? `${patient.first_name} ${patient.last_name}`
    : `Patient #${invoice.patient_id.slice(0, 8).toUpperCase()}`;
  const clinicName = clinic?.name || 'Clinic';

  const items: LineItem[] = (invoice.items as LineItem[] | undefined)?.length
    ? (invoice.items as LineItem[])
    : ((invoice.line_items as unknown as LineItem[] | undefined) ?? []);

  const balance = Number(invoice.total_amount || 0) - Number(invoice.paid_amount || 0);
  const docTitle = isReceipt ? 'Payment Receipt' : 'Invoice';

  return (
    <div
      // Top-aligned and scrollable: a centred flex box cut off the toolbar
      // (Print and Close) when the document was taller than the screen (C-13).
      className="fixed inset-0 z-50 overflow-y-auto bg-midnight/60 p-4 backdrop-blur-xs sm:py-8"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`${docTitle} ${invoice.invoice_number}`}
    >
      <div className="mx-auto w-full max-w-2xl space-y-5 rounded-2xl border border-line bg-card p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        {/* Header Actions (not printed) */}
        <div className="no-print sticky -top-4 z-10 sm:-top-8 -mx-6 -mt-6 flex items-center justify-between rounded-t-2xl border-b border-line bg-card px-6 py-4 dark:bg-slate-900">
          <h2 className="font-display text-lg font-bold text-ink">
            {docTitle} · {invoice.invoice_number}
          </h2>
          <div className="flex items-center gap-2">
            <Button onClick={() => window.print()}>
              <Printer className="h-4 w-4" />
              <span>Print {isReceipt ? 'Receipt' : 'Invoice'}</span>
            </Button>
            <button
              onClick={onClose}
              aria-label="Close"
              className="cursor-pointer rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-ink"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Printable document */}
        <div className="print-area space-y-6 rounded-xl border border-line bg-white p-8 font-sans text-xs text-[#141a33]">
          <div className="flex items-start justify-between gap-6 border-b-2 border-[#0b1238] pb-4">
            <div className="flex items-center gap-3">
              {clinic?.branding_logo_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={clinic.branding_logo_url} alt="" className="h-12 w-12 rounded object-contain" />
              )}
              <h1 className="font-display text-xl font-extrabold tracking-tight text-[#0b1238]">{clinicName}</h1>
            </div>
            <div className="text-right">
              <span className="block font-display text-lg font-extrabold uppercase text-[#0b1238]">
                {isReceipt ? 'Receipt' : 'Invoice'}
              </span>
              <span className="font-mono text-[#5d6380]">Ref: {invoice.invoice_number}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 rounded-lg bg-[#f6f2ea] p-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#767b93]">Billed To</p>
              <p className="mt-0.5 text-sm font-bold">{patientName}</p>
              {patient?.phone && <p className="text-[#5d6380]">{patient.phone}</p>}
            </div>
            <div className="space-y-1 text-right">
              <p>
                <span className="text-[#5d6380]">Date: </span>
                {formatDate(invoice.issue_date)}
              </p>
              {/* A due date means nothing on a receipt for money already received. */}
              {invoice.due_date && !isReceipt && (
                <p>
                  <span className="text-[#5d6380]">Due: </span>
                  {formatDate(invoice.due_date)}
                </p>
              )}
              <p>
                <span className="text-[#5d6380]">Status: </span>
                <Badge tone={STATUS_TONE[invoice.status] ?? 'neutral'} className="capitalize">
                  {invoice.status}
                </Badge>
              </p>
            </div>
          </div>

          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-[#ebe5d8] bg-[#f6f2ea]">
                <th className="p-2.5 text-[10px] font-bold uppercase text-[#5d6380]">Description</th>
                <th className="p-2.5 text-right text-[10px] font-bold uppercase text-[#5d6380]">Qty</th>
                <th className="p-2.5 text-right text-[10px] font-bold uppercase text-[#5d6380]">Rate</th>
                <th className="p-2.5 text-right text-[10px] font-bold uppercase text-[#5d6380]">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1ece2]">
              {items.length > 0 ? (
                items.map((item, i) => (
                  <tr key={i}>
                    <td className="p-2.5 font-medium">{item.description}</td>
                    <td className="p-2.5 text-right tabular-nums">{item.quantity}</td>
                    <td className="p-2.5 text-right tabular-nums">{money(item.unit_price)}</td>
                    <td className="p-2.5 text-right font-semibold tabular-nums">{money(item.total_price)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-2.5 italic text-[#767b93]" colSpan={4}>
                    No line items recorded on this invoice.
                  </td>
                </tr>
              )}
              <tr>
                <td className="p-2.5 text-[#5d6380]" colSpan={3}>
                  Subtotal
                </td>
                <td className="p-2.5 text-right tabular-nums">{money(invoice.subtotal)}</td>
              </tr>
              {Number(invoice.discount_amount || 0) > 0 && (
                <tr>
                  <td className="p-2.5 text-[#5d6380]" colSpan={3}>
                    Discount
                  </td>
                  <td className="p-2.5 text-right tabular-nums text-[#5d6380]">- {money(invoice.discount_amount)}</td>
                </tr>
              )}
              {Number(invoice.tax_amount || 0) > 0 && (
                <tr>
                  <td className="p-2.5 text-[#5d6380]" colSpan={3}>
                    Tax
                  </td>
                  <td className="p-2.5 text-right tabular-nums text-[#5d6380]">{money(invoice.tax_amount)}</td>
                </tr>
              )}
              <tr className="border-t-2 border-[#ebe5d8] bg-[#f6f2ea] text-sm font-extrabold">
                <td className="p-3" colSpan={3}>
                  Total
                </td>
                <td className="p-3 text-right tabular-nums text-[#15623f]">{money(invoice.total_amount)}</td>
              </tr>
              {isReceipt || Number(invoice.paid_amount || 0) > 0 ? (
                <>
                  <tr>
                    <td className="p-2.5 font-semibold" colSpan={3}>
                      Paid
                    </td>
                    <td className="p-2.5 text-right font-semibold tabular-nums">{money(invoice.paid_amount)}</td>
                  </tr>
                  {balance > 0 && (
                    <tr>
                      <td className="p-2.5 font-semibold text-[#b03a2e]" colSpan={3}>
                        Balance due
                      </td>
                      <td className="p-2.5 text-right font-semibold tabular-nums text-[#b03a2e]">
                        {formatMoney(balance.toFixed(2))}
                      </td>
                    </tr>
                  )}
                </>
              ) : null}
            </tbody>
          </table>

          {isReceipt && (
            <div className="space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#767b93]">Payments received</p>
              {isLoadingPayments ? (
                <p className="text-[#767b93]">Loading payments...</p>
              ) : invoicePayments.length === 0 ? (
                <p className="italic text-[#767b93]">No payments recorded against this invoice.</p>
              ) : (
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-[#ebe5d8]">
                      <th className="p-2 text-[10px] font-bold uppercase text-[#5d6380]">Date</th>
                      <th className="p-2 text-[10px] font-bold uppercase text-[#5d6380]">Mode</th>
                      <th className="p-2 text-[10px] font-bold uppercase text-[#5d6380]">Reference</th>
                      <th className="p-2 text-right text-[10px] font-bold uppercase text-[#5d6380]">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f1ece2]">
                    {[...invoicePayments]
                      .sort((a, b) => String(a.payment_date).localeCompare(String(b.payment_date)))
                      .map((p) => (
                        <tr key={p.id}>
                          <td className="p-2">{formatDate(p.payment_date)}</td>
                          <td className="p-2">{METHOD_LABEL[p.payment_method] ?? p.payment_method}</td>
                          <td className="p-2 font-mono text-[11px]">{p.transaction_reference || '-'}</td>
                          <td className="p-2 text-right tabular-nums">{money(p.amount)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {invoice.notes && (
            <p className="rounded-lg border border-[#ebe5d8] p-3 text-[#454b66]">
              <span className="font-semibold">Notes: </span>
              {invoice.notes}
            </p>
          )}

          <div className="flex items-end justify-between border-t border-[#ebe5d8] pt-8 text-[11px] text-[#767b93]">
            {/* Clinics have no digital signature, so no signature line (C-19). */}
            <p>This is a computer-generated {isReceipt ? 'receipt' : 'invoice'} and does not need a signature.</p>
            <p>Thank you for visiting {clinicName}.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
