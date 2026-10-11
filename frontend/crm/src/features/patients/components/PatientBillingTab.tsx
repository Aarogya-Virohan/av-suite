'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';
import { useInvoices } from '../../billing/api';
import type { Invoice, InvoiceStatus } from '../../../types/api';
import { Badge, type BadgeTone, Card } from '../../../components/ui/brand';
import { formatMoney } from '../../../lib/money';
import { hasCapability, usePermissionSubscription } from '../../../config/permissions';

const TONE: Record<InvoiceStatus, BadgeTone> = {
  paid: 'ok',
  partial: 'warn',
  unpaid: 'danger',
  overdue: 'danger',
  issued: 'info',
  draft: 'neutral',
  cancelled: 'neutral',
};
const money = (v: number | string | null | undefined) => formatMoney(v == null ? '0' : String(v));
const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

/** Replaces the "Not implemented yet" placeholder with this patient's real invoices. */
export function PatientBillingTab({ patientId }: { patientId: string }) {
  usePermissionSubscription(); // see Decisions.md D-013
  const canView = hasCapability('invoices.view');
  const { data: invoices = [], isLoading } = useInvoices(canView);
  const mine = (invoices as Invoice[])
    .filter((inv) => inv.patient_id === patientId)
    .sort((a, b) => String(b.issue_date).localeCompare(String(a.issue_date)));

  if (!canView) {
    return <Card className="p-6 text-sm text-muted">You do not have permission to view invoices.</Card>;
  }
  if (isLoading) {
    return (
      <Card className="flex items-center gap-2 p-6 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-grove" /> Loading invoices...
      </Card>
    );
  }

  const balanceDue = Math.round(
    mine
      .filter((inv) => inv.status !== 'cancelled')
      .reduce((sum, inv) => sum + (Number(inv.total_amount || 0) - Number(inv.paid_amount || 0)), 0) * 100,
  ) / 100;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h3 className="font-display text-base font-bold text-ink">Invoices</h3>
        <span className="text-sm text-muted">
          Balance due: <strong className={balanceDue > 0 ? 'text-danger' : 'text-ink'}>{formatMoney(balanceDue.toFixed(2))}</strong>
        </span>
      </div>
      {mine.length === 0 ? (
        <p className="p-8 text-center text-sm text-muted">No invoices for this patient yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-canvas/60">
                {['Invoice', 'Date', 'Total', 'Paid', 'Status'].map((h) => (
                  <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {mine.map((inv) => (
                <tr key={inv.id}>
                  <td className="px-5 py-3 font-semibold text-ink">{inv.invoice_number}</td>
                  <td className="px-5 py-3 text-ink-2">{inv.issue_date ? dateFmt.format(new Date(inv.issue_date)) : '-'}</td>
                  <td className="px-5 py-3 tabular-nums text-ink-2">{money(inv.total_amount)}</td>
                  <td className="px-5 py-3 font-semibold tabular-nums text-ink">{money(inv.paid_amount)}</td>
                  <td className="px-5 py-3">
                    <Badge tone={TONE[inv.status] ?? 'neutral'} className="capitalize">
                      {inv.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
