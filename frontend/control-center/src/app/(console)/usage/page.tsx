'use client';

import React, { Suspense, useCallback } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { FieldLabel, inputClass, PageHeader } from '@/components/ui/brand';
import { DateField } from '@/components/forms/DateField';
import { productLabel, useProductCatalog } from '@/features/catalog/hooks';
import { useClinicNames, useUsage } from '@/features/usage/hooks';
import { cn } from '@/lib/cn';
import { ISO_DAY as DATE_PATTERN } from '@/lib/dates';
import { formatDate, formatNumber, usageEventLabel } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import { PAGE_SIZE_MAX, UI_PAGE_SIZE, type UsageRow } from '@/lib/platform-api/types';

export default function UsagePage() {
  return (
    <RequirePermission permission="platform.usage.read">
      <Suspense>
        <Usage />
      </Suspense>
    </RequirePermission>
  );
}

function positiveInt(value: string | null, fallback: number, max = Number.MAX_SAFE_INTEGER): number {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 ? Math.min(n, max) : fallback;
}

type UsageTableRow = UsageRow & { id: string };

function Usage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const catalog = useProductCatalog();

  const productKey = searchParams.get('product_key') ?? '';
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

  const dateError = dateFrom && dateTo && dateTo < dateFrom ? 'The end date is before the start date.' : null;
  const query = useUsage({
    product_key: productKey || undefined,
    clinic_id: clinicId || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
    page_size: pageSize,
  });

  const rows: UsageTableRow[] = (query.data?.data ?? []).map((r) => ({ ...r, id: `${r.date}|${r.clinic_id}|${r.product_key}|${r.event_type}` }));
  const clinicNames = useClinicNames(rows.map((r) => r.clinic_id));

  const columns: Column<UsageTableRow>[] = [
    { key: 'date', header: 'Day', render: (r) => <span className="whitespace-nowrap">{formatDate(r.date)}</span> },
    {
      key: 'clinic',
      header: 'Clinic',
      render: (r) => (
        <Link href={`/clinics/${r.clinic_id}`} className="font-medium text-grove hover:text-grove-hover">
          {clinicNames.get(r.clinic_id) ?? 'Clinic'}
        </Link>
      ),
    },
    { key: 'product', header: 'Tool', render: (r) => productLabel(catalog.byKey, r.product_key) },
    { key: 'event', header: 'Event', render: (r) => usageEventLabel(r.event_type) },
    { key: 'count', header: 'Count', render: (r) => <span className="tabular-nums">{formatNumber(r.count)}</span> },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Usage" subtitle="Event counts per day, clinic and tool. Counts only: no patient names, phones or clinical data." />

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <FieldLabel htmlFor="usage-product">Tool</FieldLabel>
          <select
            id="usage-product"
            value={productKey}
            onChange={(e) => setParams({ product_key: e.target.value, page: undefined })}
            className={cn(inputClass, 'w-auto')}
          >
            <option value="">All tools</option>
            <option value="platform">Platform core</option>
            {catalog.products.map((p) => (
              <option key={p.key} value={p.key}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor="usage-from">From</FieldLabel>
          <DateField
            id="usage-from"
            value={dateFrom}
            onChange={(v) => {
              if (v === '' || DATE_PATTERN.test(v)) setParams({ date_from: v, page: undefined });
            }}
            className="w-44"
          />
        </div>
        <div>
          <FieldLabel htmlFor="usage-to">To</FieldLabel>
          <DateField
            id="usage-to"
            value={dateTo}
            onChange={(v) => {
              if (v === '' || DATE_PATTERN.test(v)) setParams({ date_to: v, page: undefined });
            }}
            invalid={!!dateError}
            className="w-44"
          />
        </div>
        {productKey || dateFrom || dateTo || clinicId ? (
          <button type="button" onClick={() => router.replace(pathname)} className="h-10 text-xs font-semibold text-grove hover:text-grove-hover">
            Clear filters
          </button>
        ) : null}
      </div>
      {dateError ? <p className="-mt-3 text-xs font-medium text-danger">{dateError}</p> : null}
      {clinicId ? <p className="-mt-3 text-xs text-muted">Showing one clinic only.</p> : null}

      {query.isError ? (
        <ErrorCard message={errorMessage(query.error, 'Could not load usage.')} onRetry={() => query.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={dateError ? [] : rows}
          isLoading={query.isLoading}
          emptyMessage={dateError ?? 'No usage matches these filters.'}
          totalItems={dateError ? 0 : query.data?.meta.total ?? 0}
          currentPage={page}
          pageSize={pageSize}
          onPageChange={(p) => setParams({ page: p === 1 ? undefined : p })}
          onPageSizeChange={(size) => setParams({ page_size: size === UI_PAGE_SIZE ? undefined : size, page: undefined })}
        />
      )}
    </div>
  );
}
