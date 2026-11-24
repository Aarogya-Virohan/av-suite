'use client';

import React from 'react';
import Link from 'next/link';
import { Activity, Building2, Hospital, Loader2, PauseCircle } from 'lucide-react';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { Card, CardHeader, KpiCard, PageHeader } from '@/components/ui/brand';
import { useOverview } from '@/features/overview/hooks';
import { productLabel, useProductCatalog } from '@/features/catalog/hooks';
import { auditActionLabel, auditProductKey, formatNumber, formatRelative, ORGANIZATION_TYPE_LABEL } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import { ORGANIZATION_TYPES } from '@/lib/platform-api/types';

export default function OverviewPage() {
  return (
    <RequirePermission permission="platform.usage.read">
      <Overview />
    </RequirePermission>
  );
}

function Overview() {
  const overview = useOverview();
  const catalog = useProductCatalog();

  if (overview.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted">
        <Loader2 className="h-5 w-5 animate-spin text-grove" /> Loading overview...
      </div>
    );
  }
  if (overview.isError || !overview.data) {
    return <ErrorCard message={errorMessage(overview.error, 'Could not load the overview.')} onRetry={() => overview.refetch()} />;
  }

  const data = overview.data;
  const effectiveByKey = new Map(data.products.map((p) => [p.product_key, p.effective_clinics]));
  const activeClinics = Math.max(data.clinics.active, 1);

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" subtitle="Customers, tool access and recent console activity across the platform." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          hero
          label="Organizations"
          value={formatNumber(data.organizations.total)}
          icon={Building2}
          footer={<span className="text-[#b9c0e0]">{formatNumber(data.organizations.active)} active</span>}
        />
        <KpiCard
          label="Clinics"
          value={formatNumber(data.clinics.total)}
          icon={Hospital}
          tone="teal"
          footer={<span className="text-muted">{formatNumber(data.clinics.active)} active</span>}
        />
        <KpiCard
          label="Suspended"
          value={formatNumber(data.organizations.suspended + data.clinics.suspended)}
          icon={PauseCircle}
          tone="danger"
          footer={
            <span className="text-muted">
              {formatNumber(data.organizations.suspended)} organizations · {formatNumber(data.clinics.suspended)} clinics
            </span>
          }
        />
        <KpiCard
          label="Usage events, last 30 days"
          value={formatNumber(data.usage_last_30_days)}
          icon={Activity}
          tone="info"
          footer={<span className="text-muted">Metadata only, no patient data</span>}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <CardHeader title="Tool access" action={<span className="text-xs text-muted">Effective in active clinics</span>} />
          {catalog.isLoading ? (
            <p className="py-6 text-center text-sm text-muted">Loading tools...</p>
          ) : (
            <ul className="space-y-3.5">
              {catalog.products.map((product) => {
                const count = effectiveByKey.get(product.key) ?? 0;
                return (
                  <li key={product.key}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span className="font-medium text-ink">{product.name}</span>
                      <span className="tabular-nums text-ink-2">{formatNumber(count)}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-grove" style={{ width: `${Math.min(100, (count / activeClinics) * 100)}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <CardHeader title="Organizations by type" />
          <ul className="divide-y divide-line-soft">
            {ORGANIZATION_TYPES.map((type) => (
              <li key={type} className="flex items-center justify-between py-2.5 text-sm">
                <Link href={`/organizations?type=${type}`} className="text-ink-2 hover:text-grove">
                  {ORGANIZATION_TYPE_LABEL[type]}
                </Link>
                <span className="font-semibold tabular-nums text-ink">{formatNumber(data.organizations.by_type[type] ?? 0)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="p-5">
        <CardHeader
          title="Recent console activity"
          action={
            <Link href="/audit-logs" className="text-xs font-semibold text-grove hover:text-grove-hover">
              Open audit log
            </Link>
          }
        />
        {data.recent_audit.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">No changes yet.</p>
        ) : (
          <ul className="divide-y divide-line-soft">
            {data.recent_audit.map((row) => (
              <li key={row.id} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-3 text-sm">
                <div className="min-w-0">
                  <p className="font-semibold text-ink">
                    {auditActionLabel(row.action)}
                    {auditProductKey(row.details) ? (
                      <span className="font-normal text-muted"> · {productLabel(catalog.byKey, auditProductKey(row.details) as string)}</span>
                    ) : null}
                  </p>
                  <p className="mt-0.5 text-xs text-muted">
                    {row.operator_name ?? 'System'}
                    {row.reason ? <> · &ldquo;{row.reason}&rdquo;</> : null}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-muted">{formatRelative(row.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
