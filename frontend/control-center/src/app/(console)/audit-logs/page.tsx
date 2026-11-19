'use client';

import React, { Suspense, useCallback, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { SlideOver } from '@/components/ui/SlideOver';
import { FieldLabel, inputClass, PageHeader } from '@/components/ui/brand';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { useAuditLogs } from '@/features/audit/hooks';
import { productLabel, useProductCatalog } from '@/features/catalog/hooks';
import { useOperators } from '@/features/operators/hooks';
import { cn } from '@/lib/cn';
import { AUDIT_ACTIONS, auditActionLabel, formatDateTime } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import { PAGE_SIZE_MAX, UI_PAGE_SIZE, type AuditLog } from '@/lib/platform-api/types';
import { useCan } from '@/store/session';

export default function AuditLogsPage() {
  return (
    <RequirePermission permission="platform.audit.read">
      <Suspense>
        <AuditLogs />
      </Suspense>
    </RequirePermission>
  );
}

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function positiveInt(value: string | null, fallback: number, max = Number.MAX_SAFE_INTEGER): number {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 ? Math.min(n, max) : fallback;
}

function AuditLogs() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const canListOperators = useCan('platform.operators.manage');
  const catalog = useProductCatalog();
  const [open, setOpen] = useState<AuditLog | null>(null);

  const action = searchParams.get('action') ?? '';
  const operatorId = searchParams.get('operator_id') ?? '';
  const organizationId = searchParams.get('organization_id') ?? '';
  const clinicId = searchParams.get('clinic_id') ?? '';
  const dateFromRaw = searchParams.get('date_from') ?? '';
  const dateToRaw = searchParams.get('date_to') ?? '';
  const dateFrom = DATE_PATTERN.test(dateFromRaw) ? dateFromRaw : '';
  const dateTo = DATE_PATTERN.test(dateToRaw) ? dateToRaw : '';
  const page = positiveInt(searchParams.get('page'), 1);
  const pageSize = positiveInt(searchParams.get('page_size'), UI_PAGE_SIZE, PAGE_SIZE_MAX);

  const setParams = useCallback(
    (changes: Record<string, string | number | undefined>) => {
      const next = new URLSearchParams(searchParams.toString());
      Object.entries(changes).forEach(([key, value]) => {
        if (value === undefined || value === '') next.delete(key);
        else next.set(key, String(value));
      });
      const q = next.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  // Support cannot list operators (platform.operators.manage), so the
  // operator filter is offered to Owners only.
  const operators = useOperators({ page: 1, page_size: PAGE_SIZE_MAX }, canListOperators);
  const query = useAuditLogs({
    action: action || undefined,
    operator_id: operatorId || undefined,
    organization_id: organizationId || undefined,
    clinic_id: clinicId || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
    page_size: pageSize,
  });

  const dateError = dateFrom && dateTo && dateTo < dateFrom ? 'The end date is before the start date.' : null;

  const columns: Column<AuditLog>[] = [
    { key: 'created_at', header: 'When', render: (a) => <span className="whitespace-nowrap">{formatDateTime(a.created_at)}</span> },
    { key: 'operator', header: 'Operator', render: (a) => a.operator_name ?? 'System' },
    {
      key: 'action',
      header: 'Action',
      render: (a) => (
        <div>
          <p className="font-semibold text-ink">{auditActionLabel(a.action)}</p>
          {typeof a.details.product_key === 'string' ? <p className="text-xs text-muted">{productLabel(catalog.byKey, a.details.product_key)}</p> : null}
        </div>
      ),
    },
    {
      key: 'target',
      header: 'Target',
      render: (a) => <TargetLink log={a} />,
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (a) => <span className="line-clamp-2 max-w-[340px]">{a.reason ?? '-'}</span>,
    },
  ];

  const scoped = organizationId || clinicId;

  return (
    <div className="space-y-6">
      <PageHeader title="Audit log" subtitle="Every console change, who made it and why. Append-only." />

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <FieldLabel htmlFor="audit-action">Action</FieldLabel>
          <select
            id="audit-action"
            value={action}
            onChange={(e) => setParams({ action: e.target.value, page: undefined })}
            className={cn(inputClass, 'w-auto')}
          >
            <option value="">All actions</option>
            {AUDIT_ACTIONS.map((a) => (
              <option key={a} value={a}>
                {auditActionLabel(a)}
              </option>
            ))}
          </select>
        </div>
        {canListOperators ? (
          <div>
            <FieldLabel htmlFor="audit-operator">Operator</FieldLabel>
            <select
              id="audit-operator"
              value={operatorId}
              onChange={(e) => setParams({ operator_id: e.target.value, page: undefined })}
              className={cn(inputClass, 'w-auto')}
            >
              <option value="">All operators</option>
              {(operators.data?.data ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <div>
          <FieldLabel htmlFor="audit-from">From</FieldLabel>
          <input
            id="audit-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setParams({ date_from: e.target.value, page: undefined })}
            className={cn(inputClass, 'w-auto')}
          />
        </div>
        <div>
          <FieldLabel htmlFor="audit-to">To</FieldLabel>
          <input
            id="audit-to"
            type="date"
            value={dateTo}
            onChange={(e) => setParams({ date_to: e.target.value, page: undefined })}
            className={cn(inputClass, 'w-auto', dateError && 'border-danger')}
          />
        </div>
        {action || operatorId || dateFrom || dateTo || scoped ? (
          <button type="button" onClick={() => router.replace(pathname)} className="h-10 text-xs font-semibold text-grove hover:text-grove-hover">
            Clear filters
          </button>
        ) : null}
      </div>
      {dateError ? <p className="-mt-3 text-xs font-medium text-danger">{dateError}</p> : null}
      {scoped ? (
        <p className="-mt-3 text-xs text-muted">Showing changes for one {clinicId ? 'clinic' : 'organization'} only.</p>
      ) : null}

      {query.isError ? (
        <ErrorCard message={errorMessage(query.error, 'Could not load the audit log.')} onRetry={() => query.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={dateError ? [] : query.data?.data ?? []}
          isLoading={query.isLoading}
          emptyMessage={dateError ?? 'No changes match these filters.'}
          totalItems={dateError ? 0 : query.data?.meta.total ?? 0}
          currentPage={page}
          pageSize={pageSize}
          onPageChange={(p) => setParams({ page: p === 1 ? undefined : p })}
          onPageSizeChange={(size) => setParams({ page_size: size === UI_PAGE_SIZE ? undefined : size, page: undefined })}
          onRowClick={setOpen}
        />
      )}

      <SlideOver isOpen={open !== null} onClose={() => setOpen(null)} title={open ? auditActionLabel(open.action) : ''} subtitle={open ? formatDateTime(open.created_at) : undefined}>
        {open ? (
          <dl className="space-y-4 text-sm">
            <Row label="Operator" value={open.operator_name ?? 'System'} />
            <Row label="Reason" value={open.reason ?? '-'} />
            <Row label="Target" value={<TargetLink log={open} />} />
            <Row label="Action code" value={<code className="font-mono text-xs">{open.action}</code>} />
            <Row label="IP / client" value={[open.ip, open.user_agent].filter(Boolean).join(' · ') || '-'} />
            <div>
              <dt className="text-xs font-medium text-muted">Details</dt>
              <dd className="mt-1">
                <pre className="max-h-80 overflow-auto rounded-xl border border-line bg-canvas p-3 font-mono text-xs text-ink-2">
                  {JSON.stringify(open.details, null, 2)}
                </pre>
              </dd>
            </div>
          </dl>
        ) : null}
      </SlideOver>
    </div>
  );
}

function TargetLink({ log }: { log: AuditLog }) {
  if (log.clinic_id) {
    return (
      <Link href={`/clinics/${log.clinic_id}`} onClick={(e) => e.stopPropagation()} className="font-medium text-grove hover:text-grove-hover">
        Open clinic
      </Link>
    );
  }
  if (log.organization_id) {
    return (
      <Link
        href={`/organizations/${log.organization_id}`}
        onClick={(e) => e.stopPropagation()}
        className="font-medium text-grove hover:text-grove-hover"
      >
        Open organization
      </Link>
    );
  }
  return <span className="capitalize text-ink-2">{log.target_type}</span>;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="mt-1 break-words text-ink">{value}</dd>
    </div>
  );
}
