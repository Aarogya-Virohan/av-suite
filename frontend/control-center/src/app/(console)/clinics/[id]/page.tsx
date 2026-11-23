'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Activity, ArrowLeft, Ban, Boxes, Clock, Loader2, Pencil, Play, Users } from 'lucide-react';
import { toast } from 'sonner';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { ReasonActionSlideOver } from '@/components/forms/ReasonActionSlideOver';
import { Badge, Button, Card, CardHeader, KpiCard, PageHeader } from '@/components/ui/brand';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { productLabel, useProductCatalog } from '@/features/catalog/hooks';
import { EntitlementEditor } from '@/features/clinics/EntitlementEditor';
import { ACCESS_LABEL, ACCESS_TONE, accessState, isoToUntilDate } from '@/features/clinics/entitlement';
import { useClinic, useSetClinicStatus } from '@/features/clinics/hooks';
import { formatDate, formatNumber, formatRelative, STATUS_LABEL, STATUS_TONE } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import type { Entitlement, ProductCatalogItem } from '@/lib/platform-api/types';
import { useCan } from '@/store/session';

export default function ClinicDetailPage() {
  return (
    <RequirePermission permission="platform.organizations.read">
      <ClinicDetail />
    </RequirePermission>
  );
}

function ClinicDetail() {
  const { id } = useParams<{ id: string }>();
  const query = useClinic(id);
  const catalog = useProductCatalog();
  const canManage = useCan('platform.organizations.manage');
  const canGrant = useCan('platform.entitlements.manage');
  const setStatus = useSetClinicStatus(id);
  const [statusOpen, setStatusOpen] = useState(false);
  const [editing, setEditing] = useState<ProductCatalogItem | null>(null);

  if (query.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted">
        <Loader2 className="h-5 w-5 animate-spin text-grove" /> Loading clinic...
      </div>
    );
  }
  if (query.isError || !query.data) {
    return <ErrorCard message={errorMessage(query.error, 'Could not load this clinic.')} onRetry={() => query.refetch()} />;
  }

  const clinic = query.data;
  const suspended = clinic.status === 'suspended';
  const orgSuspended = clinic.organization_status === 'suspended';
  const entitlementByKey = new Map<string, Entitlement>(clinic.products.map((e) => [e.product_key, e]));
  const blocked = suspended || orgSuspended;
  const effectiveCount = blocked ? 0 : catalog.products.filter((p) => accessState(entitlementByKey.get(p.key)) === 'active').length;
  const maxUsage = Math.max(1, ...clinic.usage.by_product.map((u) => u.events));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/organizations/${clinic.organization_id}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {clinic.organization_name}
        </Link>
        <Link href={`/audit-logs?clinic_id=${clinic.id}`} className="text-xs font-semibold text-grove hover:text-grove-hover">
          Audit log for this clinic
        </Link>
      </div>

      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {clinic.name}
            <Badge tone={STATUS_TONE[clinic.status]}>{STATUS_LABEL[clinic.status]}</Badge>
          </span>
        }
        subtitle={`${clinic.slug} · added ${formatDate(clinic.created_at)}`}
        actions={
          canManage ? (
            <Button variant="secondary" onClick={() => setStatusOpen(true)}>
              {suspended ? <Play className="h-4 w-4" /> : <Ban className="h-4 w-4" />}
              <span>{suspended ? 'Activate' : 'Suspend'}</span>
            </Button>
          ) : null
        }
      />

      {orgSuspended ? (
        <p className="rounded-xl border border-danger/20 bg-danger-wash px-4 py-3 text-sm font-medium text-danger">
          The organization is suspended, so this clinic is blocked whatever its own status. Activate it from the{' '}
          <Link href={`/organizations/${clinic.organization_id}`} className="underline">
            organization page
          </Link>
          .
        </p>
      ) : suspended ? (
        <p className="rounded-xl border border-danger/20 bg-danger-wash px-4 py-3 text-sm font-medium text-danger">
          This clinic is suspended. Its staff are blocked and its booking page returns not found. No data is deleted.
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Staff" value={formatNumber(clinic.staff_count)} icon={Users} tone="teal" />
        <KpiCard label="Last activity" value={formatRelative(clinic.last_activity_at)} icon={Clock} tone="info" />
        <KpiCard
          label={`Usage events, last ${clinic.usage.window_days} days`}
          value={formatNumber(clinic.usage.total_events)}
          icon={Activity}
          tone="grove"
        />
        <KpiCard label="Tools active" value={`${effectiveCount} / ${catalog.products.length}`} icon={Boxes} tone="warn" />
      </div>

      <Card className="overflow-hidden">
        <div className="px-5 pt-5">
          <CardHeader
            title="Tools"
            action={<span className="text-xs text-muted">Granted from this console only (marketplace rules: M-1, open)</span>}
          />
        </div>
        {catalog.isLoading ? (
          <p className="px-5 pb-6 text-sm text-muted">Loading tools...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-y border-line bg-canvas/60">
                  {['Tool', 'Access', 'Valid from', 'Valid until', 'Last change', ''].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft text-sm">
                {catalog.products.map((product) => {
                  const e = entitlementByKey.get(product.key) ?? null;
                  const state = accessState(e);
                  return (
                    <tr key={product.key}>
                      <td className="px-5 py-3.5">
                        <p className="font-semibold text-ink">{product.name}</p>
                        <p className="text-xs text-muted">{product.category}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        {/* A granted tool is still unusable while the clinic or its organization is suspended. */}
                        {state === 'active' && orgSuspended ? (
                          <Badge tone="neutral">Blocked by organization</Badge>
                        ) : state === 'active' && suspended ? (
                          <Badge tone="neutral">Blocked by clinic</Badge>
                        ) : (
                          <Badge tone={ACCESS_TONE[state]}>{ACCESS_LABEL[state]}</Badge>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-ink-2">{e ? (e.valid_from ? formatDate(e.valid_from) : 'No limit') : '-'}</td>
                      <td className="px-5 py-3.5 text-ink-2">
                        {/* Stored bound is exclusive; show the last day with access. */}
                        {e ? (e.valid_until ? formatDate(`${isoToUntilDate(e.valid_until)}T12:00:00+05:30`) : 'No limit') : '-'}
                      </td>
                      <td className="px-5 py-3.5 text-ink-2">{e ? formatRelative(e.updated_at) : '-'}</td>
                      <td className="px-5 py-3.5 text-right">
                        {canGrant ? (
                          <Button variant="ghost" className="h-8 px-3" onClick={() => setEditing(product)}>
                            <Pencil className="h-3.5 w-3.5" />
                            <span>{e ? 'Edit' : 'Grant'}</span>
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="p-5">
        <CardHeader
          title="Usage by tool"
          action={
            <Link href={`/usage?clinic_id=${clinic.id}`} className="text-xs font-semibold text-grove hover:text-grove-hover">
              Daily usage
            </Link>
          }
        />
        {clinic.usage.by_product.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">No usage in this period.</p>
        ) : (
          <ul className="space-y-3.5">
            {[...clinic.usage.by_product]
              .sort((a, b) => b.events - a.events)
              .map((u) => (
                <li key={u.product_key}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-medium text-ink">{productLabel(catalog.byKey, u.product_key)}</span>
                    <span className="tabular-nums text-ink-2">{formatNumber(u.events)}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-grove" style={{ width: `${(u.events / maxUsage) * 100}%` }} />
                  </div>
                </li>
              ))}
          </ul>
        )}
      </Card>

      <ReasonActionSlideOver
        isOpen={statusOpen}
        onClose={() => setStatusOpen(false)}
        title={suspended ? 'Activate clinic' : 'Suspend clinic'}
        subtitle={clinic.name}
        tone={suspended ? 'default' : 'danger'}
        description={
          suspended ? (
            <>Staff of this clinic can work again{orgSuspended ? ' once the organization is active too' : ''}.</>
          ) : (
            <>
              Staff of this clinic are blocked on their next request and its booking page returns not found. Other branches are not affected.
              No data is deleted.
            </>
          )
        }
        confirmLabel={suspended ? 'Activate' : 'Suspend clinic'}
        isPending={setStatus.isPending}
        serverError={setStatus.isError ? errorMessage(setStatus.error) : null}
        onConfirm={(reason) =>
          setStatus.mutate(
            { action: suspended ? 'activate' : 'suspend', reason },
            {
              onSuccess: () => {
                toast.success(suspended ? 'Clinic activated' : 'Clinic suspended');
                setStatusOpen(false);
                setStatus.reset();
              },
            },
          )
        }
      />

      <EntitlementEditor
        clinicId={clinic.id}
        clinicName={clinic.name}
        product={editing}
        current={editing ? entitlementByKey.get(editing.key) ?? null : null}
        onClose={() => setEditing(null)}
      />
    </div>
  );
}
