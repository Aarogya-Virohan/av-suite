'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import {
  cancelBlockReason,
  useCancelInvoice,
  useInvoices,
  usePackages,
  usePayments,
  useVoidPayment,
  VOID_REASON_MIN,
} from '../../../features/billing/api';
import { ReasonSlideOver } from '../../../features/billing/components/ReasonSlideOver';
import { toast } from 'sonner';
import { CreateInvoiceSlideOver } from '../../../features/billing/components/CreateInvoiceSlideOver';
import { RecordPaymentSlideOver } from '../../../features/billing/components/RecordPaymentSlideOver';
import { InvoicePreviewModal } from '../../../features/billing/components/InvoicePreviewModal';
import { Invoice, Payment, Package, InvoiceStatus } from '../../../types/api';
import { Plus, CreditCard, FileText, Package as PackageIcon, Eye, Printer, Ban, Undo2 } from 'lucide-react';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { Avatar, Badge, type BadgeTone, Button, PageHeader, SegmentGroup, SegmentTab } from '../../../components/ui/brand';
import { formatMoney } from '../../../lib/money';
import { cn } from '../../../lib/cn';

type TabKey = 'invoices' | 'payments' | 'packages';

/** API money fields are Decimal strings; older code paths may still pass numbers. */
const money = (value: number | string | null | undefined) => formatMoney(value == null ? '0' : String(value));

const INVOICE_TONE: Record<InvoiceStatus, BadgeTone> = {
  paid: 'ok',
  partial: 'warn',
  unpaid: 'danger',
  overdue: 'danger',
  issued: 'info',
  draft: 'neutral',
  cancelled: 'neutral',
};

const paymentDateFormat = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

function formatPaymentDate(value: string | null | undefined) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : paymentDateFormat.format(date);
}

const SMALL_ACTION =
  'inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition-colors';

export default function BillingPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const isAllowed = canAccessModule('billing');
  const canViewInvoices = hasCapability('invoices.view');
  const canViewPayments = hasCapability('payments.view');
  const canViewPackages = hasCapability('packages.view');
  // The backend enforces these; the buttons are hidden so a role without them
  // does not open a form that can only fail (Decisions.md L-9).
  const canCreateInvoice = hasCapability('invoices.create');
  const canRecordPayment = hasCapability('payments.record');
  // CRM-4: cancel = invoices.edit, void = payments.delete (same as the server).
  const canCancelInvoice = hasCapability('invoices.edit');
  const canVoidPayment = hasCapability('payments.delete');
  const [cancelTarget, setCancelTarget] = useState<Invoice | null>(null);
  const [voidTarget, setVoidTarget] = useState<Payment | null>(null);
  const cancelInvoice = useCancelInvoice();
  const voidPayment = useVoidPayment();

  // The default tab is derived on every render, not frozen into useState:
  // capabilities can arrive after the first render, and freezing them made
  // admins land on the (empty) package tab.
  const tabs: { key: TabKey; label: string; icon: React.ElementType; visible: boolean }[] = [
    { key: 'invoices', label: 'Invoices', icon: FileText, visible: canViewInvoices },
    { key: 'payments', label: 'Payments Log', icon: CreditCard, visible: canViewPayments },
    { key: 'packages', label: 'Package Catalog', icon: PackageIcon, visible: canViewPackages },
  ];
  const visibleTabs = tabs.filter((t) => t.visible);
  const [selectedTab, setSelectedTab] = useState<TabKey | null>(null);
  const activeTab: TabKey | null =
    selectedTab && visibleTabs.some((t) => t.key === selectedTab) ? selectedTab : visibleTabs[0]?.key ?? null;

  const [isInvoiceOpen, setIsInvoiceOpen] = useState(false);
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);

  // Preview Modal state
  const [previewInvoice, setPreviewInvoice] = useState<Invoice | null>(null);
  const [previewMode, setPreviewMode] = useState<'invoice' | 'receipt'>('invoice');

  // The preview is a modal without its own route, so the browser Back button
  // used to leave Billing (founder feedback C-12). Opening it now adds a
  // history entry, Back closes the modal, and closing it pops that entry.
  // Next's own history state is copied, otherwise the App Router reloads the
  // page on popstate.
  const openPreview = (inv: Invoice, mode: 'invoice' | 'receipt') => {
    setPreviewInvoice(inv);
    setPreviewMode(mode);
    window.history.pushState({ ...(window.history.state ?? {}), avInvoicePreview: true }, '');
  };
  const closePreview = () => {
    if (window.history.state?.avInvoicePreview) window.history.back();
    else setPreviewInvoice(null);
  };
  React.useEffect(() => {
    const onPop = () => {
      if (!window.history.state?.avInvoicePreview) setPreviewInvoice(null);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const { data: invoices = [], isLoading: isLoadingInvoices } = useInvoices(canViewInvoices);
  const { data: payments = [], isLoading: isLoadingPayments } = usePayments(canViewPayments);
  const { data: packages = [], isLoading: isLoadingPackages } = usePackages(canViewPackages);
  // Names come with each invoice and payment from the API, so every row has
  // one (this replaced the first-100-patients lookup, Decisions.md L-8).
  const getPatientName = (row: { patient_id: string; patient_name?: string | null }) =>
    row.patient_name?.trim() || `Patient #${row.patient_id.slice(0, 8).toUpperCase()}`;

  const counts: Record<TabKey, number> = {
    invoices: invoices.length,
    payments: payments.length,
    packages: packages.length,
  };

  if (!isAllowed) {
    return <AccessRestricted message="Billing & invoices access is restricted for your role." />;
  }

  const invoiceColumns: Column<Invoice>[] = [
    {
      key: 'invoice_number',
      header: 'Invoice',
      render: (inv) => <span className="whitespace-nowrap font-semibold text-ink">{inv.invoice_number}</span>,
    },
    {
      key: 'patient',
      header: 'Patient',
      render: (inv) => {
        const name = getPatientName(inv);
        return (
          <div className="flex items-center gap-2.5">
            <Avatar name={name} size={30} />
            <span className="whitespace-nowrap font-medium text-ink">{name}</span>
          </div>
        );
      },
    },
    {
      key: 'total_amount',
      header: 'Total',
      render: (inv) => <span className="whitespace-nowrap tabular-nums">{money(inv.total_amount)}</span>,
    },
    {
      key: 'paid_amount',
      header: 'Paid',
      render: (inv) => <span className="whitespace-nowrap font-semibold tabular-nums text-ink">{money(inv.paid_amount)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (inv) => (
        <Badge tone={INVOICE_TONE[inv.status] ?? 'neutral'} className={cn('capitalize', inv.status === 'cancelled' && 'line-through')}>
          {inv.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (inv) => (
        <div className="flex items-center gap-2 whitespace-nowrap">
          <button
            onClick={() => openPreview(inv, 'invoice')}
            className={cn(SMALL_ACTION, 'border border-line bg-card text-ink-2 hover:bg-canvas')}
          >
            <Eye className="h-3.5 w-3.5" />
            <span>Invoice</span>
          </button>
          {(inv.status === 'paid' || inv.status === 'partial') && (
            <button
              onClick={() => openPreview(inv, 'receipt')}
              className={cn(SMALL_ACTION, 'bg-ok-wash text-ok hover:bg-[#d3eedc]')}
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Receipt</span>
            </button>
          )}
          {canCancelInvoice && inv.status !== 'cancelled' && (
            <button
              onClick={() => {
                const blocked = cancelBlockReason(inv);
                if (blocked) toast.error(`${inv.invoice_number}: ${blocked}.`);
                else setCancelTarget(inv);
              }}
              title={cancelBlockReason(inv) ?? 'Cancel this invoice'}
              aria-label={`Cancel invoice ${inv.invoice_number}`}
              className={cn(SMALL_ACTION, 'text-danger hover:bg-danger-wash', cancelBlockReason(inv) && 'opacity-50')}
            >
              <Ban className="h-3.5 w-3.5" />
              <span>Cancel</span>
            </button>
          )}
        </div>
      ),
    },
  ];

  const paymentColumns: Column<Payment>[] = [
    {
      key: 'id',
      header: 'Reference',
      render: (p) => (
        <span title={p.id} className="font-mono text-xs font-semibold text-ink-2">
          #{p.id.slice(0, 8).toUpperCase()}
        </span>
      ),
    },
    {
      key: 'patient',
      header: 'Patient',
      render: (p) => {
        const name = getPatientName(p);
        return (
          <div className="flex items-center gap-2.5">
            <Avatar name={name} size={30} />
            <span className="whitespace-nowrap font-medium text-ink">{name}</span>
          </div>
        );
      },
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (p) => <span className="whitespace-nowrap font-semibold tabular-nums text-ink">{money(p.amount)}</span>,
    },
    {
      key: 'payment_method',
      header: 'Method',
      render: (p) => (
        <Badge tone="active" className="uppercase">
          {p.payment_method}
        </Badge>
      ),
    },
    {
      key: 'payment_date',
      header: 'Date',
      render: (p) => <span className="whitespace-nowrap tabular-nums">{formatPaymentDate(p.payment_date)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (p) =>
        p.status === 'voided' ? (
          <span title={p.void_reason ?? undefined}>
            <Badge tone="neutral" className="line-through">
              Voided
            </Badge>
          </span>
        ) : (
          <Badge tone="ok">Received</Badge>
        ),
    },
  ];
  if (canVoidPayment) {
    paymentColumns.push({
      key: 'actions',
      header: 'Actions',
      render: (p) =>
        p.status === 'voided' ? (
          <span className="text-xs text-muted">-</span>
        ) : (
          <button
            onClick={() => setVoidTarget(p)}
            aria-label={`Void payment ${p.id.slice(0, 8).toUpperCase()}`}
            className={cn(SMALL_ACTION, 'text-danger hover:bg-danger-wash')}
          >
            <Undo2 className="h-3.5 w-3.5" />
            <span>Void</span>
          </button>
        ),
    });
  }

  const packageColumns: Column<Package>[] = [
    { key: 'name', header: 'Package', render: (pkg) => <span className="font-semibold text-ink">{pkg.name}</span> },
    { key: 'total_sessions', header: 'Sessions', render: (pkg) => `${pkg.total_sessions} sessions` },
    { key: 'price', header: 'Price', render: (pkg) => <span className="font-semibold tabular-nums text-ink">{money(pkg.price)}</span> },
    { key: 'validity_days', header: 'Validity', render: (pkg) => `${pkg.validity_days} days` },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Billing & Invoices"
          subtitle="Manage patient billing, payments, and packages catalog"
          actions={
            <>
              {canRecordPayment && (
                <Button variant="secondary" onClick={() => setIsPaymentOpen(true)}>
                  <CreditCard className="h-4 w-4 text-grove" />
                  <span>Record Payment</span>
                </Button>
              )}
              {canCreateInvoice && (
                <Button onClick={() => setIsInvoiceOpen(true)}>
                  <Plus className="h-4 w-4" />
                  <span>Create Invoice</span>
                </Button>
              )}
            </>
          }
        />

        {visibleTabs.length > 0 && (
          <SegmentGroup>
            {visibleTabs.map((tab) => (
              <SegmentTab
                key={tab.key}
                active={activeTab === tab.key}
                onClick={() => setSelectedTab(tab.key)}
                icon={tab.icon}
              >
                {tab.label}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold tabular-nums text-muted">
                  {counts[tab.key]}
                </span>
              </SegmentTab>
            ))}
          </SegmentGroup>
        )}

        {/* Tab Content */}
        {activeTab === 'invoices' && (
          <DataTable
            columns={invoiceColumns}
            data={invoices}
            isLoading={isLoadingInvoices}
            searchField={(inv) => `${inv.invoice_number} ${getPatientName(inv)}`}
            searchPlaceholder="Search invoices by number or patient name..."
          />
        )}

        {activeTab === 'payments' && (
          <DataTable
            columns={paymentColumns}
            data={payments}
            isLoading={isLoadingPayments}
            searchField={(p) => getPatientName(p)}
            searchPlaceholder="Search payments by patient name..."
          />
        )}

        {activeTab === 'packages' && (
          <DataTable
            columns={packageColumns}
            data={packages}
            isLoading={isLoadingPackages}
            searchField={(pkg) => pkg.name}
            searchPlaceholder="Search package catalog..."
          />
        )}

        {/* Drawers & Printable Preview Modal */}
        <CreateInvoiceSlideOver isOpen={isInvoiceOpen} onClose={() => setIsInvoiceOpen(false)} />
        <RecordPaymentSlideOver isOpen={isPaymentOpen} onClose={() => setIsPaymentOpen(false)} />
        <ReasonSlideOver
          isOpen={!!cancelTarget}
          onClose={() => setCancelTarget(null)}
          title="Cancel Invoice"
          subtitle={cancelTarget?.invoice_number}
          summary={
            cancelTarget && (
              <>
                Invoice <strong>{cancelTarget.invoice_number}</strong> for <strong>{getPatientName(cancelTarget)}</strong> (
                {money(cancelTarget.total_amount)}) will be marked cancelled. It stays in the list and cannot be reopened or moved back to
                draft.
              </>
            )
          }
          confirmLabel="Cancel Invoice"
          isPending={cancelInvoice.isPending}
          onConfirm={async (reason) => {
            if (!cancelTarget) return;
            try {
              await cancelInvoice.mutateAsync({ invoiceId: cancelTarget.id, reason });
              toast.success(`Invoice ${cancelTarget.invoice_number} cancelled`);
              setCancelTarget(null);
            } catch (err: any) {
              toast.error(err?.message || 'Could not cancel the invoice');
            }
          }}
        />
        <ReasonSlideOver
          isOpen={!!voidTarget}
          onClose={() => setVoidTarget(null)}
          title="Void Payment"
          subtitle={voidTarget ? `#${voidTarget.id.slice(0, 8).toUpperCase()}` : undefined}
          summary={
            voidTarget && (
              <>
                The payment of <strong>{money(voidTarget.amount)}</strong> from <strong>{getPatientName(voidTarget)}</strong> will be
                voided. The invoice balance goes up by the same amount. The row stays in the log, marked voided.
              </>
            )
          }
          confirmLabel="Void Payment"
          minLength={VOID_REASON_MIN}
          isPending={voidPayment.isPending}
          onConfirm={async (reason) => {
            if (!voidTarget) return;
            try {
              await voidPayment.mutateAsync({ paymentId: voidTarget.id, reason });
              toast.success('Payment voided');
              setVoidTarget(null);
            } catch (err: any) {
              toast.error(err?.message || 'Could not void the payment');
            }
          }}
        />
        <InvoicePreviewModal
          isOpen={!!previewInvoice}
          onClose={closePreview}
          invoice={previewInvoice}
          mode={previewMode}
        />
      </div>
    </AppShell>
  );
}
