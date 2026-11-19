'use client';

import React, { Suspense, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { Badge, inputClass, PageHeader } from '@/components/ui/brand';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { useOrganizations } from '@/features/organizations/hooks';
import { cn } from '@/lib/cn';
import { formatDate, ORGANIZATION_TYPE_LABEL, STATUS_LABEL, STATUS_TONE } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import {
  ACCOUNT_STATUSES,
  ORGANIZATION_TYPES,
  UI_PAGE_SIZE,
  PAGE_SIZE_MAX,
  type AccountStatus,
  type OrganizationListItem,
  type OrganizationType,
} from '@/lib/platform-api/types';

export default function OrganizationsPage() {
  return (
    <RequirePermission permission="platform.organizations.read">
      <Suspense>
        <OrganizationList />
      </Suspense>
    </RequirePermission>
  );
}

function positiveInt(value: string | null, fallback: number, max = Number.MAX_SAFE_INTEGER): number {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 ? Math.min(n, max) : fallback;
}

function OrganizationList() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Filters live in the URL, so a filtered list can be shared or reloaded.
  const search = searchParams.get('search') ?? '';
  const typeParam = searchParams.get('type');
  const statusParam = searchParams.get('status');
  const type = ORGANIZATION_TYPES.includes(typeParam as OrganizationType) ? (typeParam as OrganizationType) : undefined;
  const status = ACCOUNT_STATUSES.includes(statusParam as AccountStatus) ? (statusParam as AccountStatus) : undefined;
  const page = positiveInt(searchParams.get('page'), 1);
  const pageSize = positiveInt(searchParams.get('page_size'), UI_PAGE_SIZE, PAGE_SIZE_MAX);

  const setParams = useCallback(
    (changes: Record<string, string | number | undefined>) => {
      const next = new URLSearchParams(searchParams.toString());
      Object.entries(changes).forEach(([key, value]) => {
        if (value === undefined || value === '') next.delete(key);
        else next.set(key, String(value));
      });
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  const onSearchChange = useCallback(
    (term: string) => {
      if (term.trim() === search) return;
      setParams({ search: term.trim() || undefined, page: undefined });
    },
    [search, setParams],
  );

  const query = useOrganizations({ search: search || undefined, type, status, page, page_size: pageSize });

  const columns: Column<OrganizationListItem>[] = [
    {
      key: 'name',
      header: 'Organization',
      render: (o) => (
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{o.name}</p>
          <p className="truncate text-xs text-muted">{o.slug}</p>
        </div>
      ),
    },
    { key: 'type', header: 'Type', render: (o) => ORGANIZATION_TYPE_LABEL[o.type] },
    { key: 'status', header: 'Status', render: (o) => <Badge tone={STATUS_TONE[o.status]}>{STATUS_LABEL[o.status]}</Badge> },
    {
      key: 'clinics',
      header: 'Clinics',
      render: (o) => (
        <span className="tabular-nums">
          {o.active_clinic_count}
          <span className="text-muted"> / {o.clinic_count} active</span>
        </span>
      ),
    },
    { key: 'created_at', header: 'Customer since', render: (o) => formatDate(o.created_at) },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organizations"
        subtitle="Every customer account and its clinics. Open one to manage branches and status."
        actions={
          <>
            <select
              aria-label="Filter by type"
              value={type ?? 'all'}
              onChange={(e) => setParams({ type: e.target.value === 'all' ? undefined : e.target.value, page: undefined })}
              className={cn(inputClass, 'w-auto')}
            >
              <option value="all">All types</option>
              {ORGANIZATION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {ORGANIZATION_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by status"
              value={status ?? 'all'}
              onChange={(e) => setParams({ status: e.target.value === 'all' ? undefined : e.target.value, page: undefined })}
              className={cn(inputClass, 'w-auto')}
            >
              <option value="all">All statuses</option>
              {ACCOUNT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </>
        }
      />

      {query.isError ? (
        <ErrorCard message={errorMessage(query.error, 'Could not load organizations.')} onRetry={() => query.refetch()} />
      ) : (
        <DataTable
          initialSearch={search}
          columns={columns}
          data={query.data?.data ?? []}
          isLoading={query.isLoading}
          emptyMessage={search || type || status ? 'No organizations match these filters.' : 'No organizations yet.'}
          searchPlaceholder="Search by name or slug..."
          onSearchChange={onSearchChange}
          totalItems={query.data?.meta.total ?? 0}
          currentPage={page}
          pageSize={pageSize}
          onPageChange={(p) => setParams({ page: p === 1 ? undefined : p })}
          onPageSizeChange={(size) => setParams({ page_size: size === UI_PAGE_SIZE ? undefined : size, page: undefined })}
          onRowClick={(o) => router.push(`/organizations/${o.id}`)}
        />
      )}
    </div>
  );
}
