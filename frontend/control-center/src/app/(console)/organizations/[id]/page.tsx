'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Ban, Loader2, Play, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { ReasonActionSlideOver } from '@/components/forms/ReasonActionSlideOver';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { Badge, Button, Card, CardHeader, PageHeader } from '@/components/ui/brand';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { AddBranchSlideOver } from '@/features/organizations/AddBranchSlideOver';
import { useOrganization, useSetOrganizationStatus } from '@/features/organizations/hooks';
import { formatDate, formatRelative, ORGANIZATION_TYPE_LABEL, STATUS_LABEL, STATUS_TONE } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import type { ClinicListItem } from '@/lib/platform-api/types';
import { useCan } from '@/store/session';

export default function OrganizationDetailPage() {
  return (
    <RequirePermission permission="platform.organizations.read">
      <OrganizationDetail />
    </RequirePermission>
  );
}

const CLINIC_TYPE_LABEL: Record<ClinicListItem['type'], string> = { clinic: 'Clinic', solo: 'Solo practice', personal: 'Personal' };

function OrganizationDetail() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const canManage = useCan('platform.organizations.manage');
  const query = useOrganization(id);
  const setStatus = useSetOrganizationStatus(id);
  const [statusOpen, setStatusOpen] = useState(false);
  const [branchOpen, setBranchOpen] = useState(false);

  if (query.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted">
        <Loader2 className="h-5 w-5 animate-spin text-grove" /> Loading organization...
      </div>
    );
  }
  if (query.isError || !query.data) {
    return <ErrorCard message={errorMessage(query.error, 'Could not load this organization.')} onRetry={() => query.refetch()} />;
  }

  const org = query.data;
  const suspended = org.status === 'suspended';
  const action = suspended ? 'activate' : 'suspend';

  const columns: Column<ClinicListItem>[] = [
    {
      key: 'name',
      header: 'Clinic',
      render: (c) => (
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{c.name}</p>
          <p className="truncate text-xs text-muted">{c.slug}</p>
        </div>
      ),
    },
    { key: 'type', header: 'Type', render: (c) => CLINIC_TYPE_LABEL[c.type] },
    {
      key: 'status',
      header: 'Status',
      // An active clinic of a suspended organization is blocked too (acceptance 6).
      render: (c) =>
        suspended && c.status === 'active' ? (
          <Badge tone="neutral">Blocked by organization</Badge>
        ) : (
          <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>
        ),
    },
    { key: 'staff_count', header: 'Staff', render: (c) => <span className="tabular-nums">{c.staff_count}</span> },
    { key: 'last_activity_at', header: 'Last activity', render: (c) => formatRelative(c.last_activity_at) },
  ];

  return (
    <div className="space-y-6">
      <Link href="/organizations" className="inline-flex items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover">
        <ArrowLeft className="h-3.5 w-3.5" /> Organizations
      </Link>

      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {org.name}
            <Badge tone={STATUS_TONE[org.status]}>{STATUS_LABEL[org.status]}</Badge>
          </span>
        }
        subtitle={`${ORGANIZATION_TYPE_LABEL[org.type]} · ${org.slug}`}
        actions={
          canManage ? (
            <>
              <Button variant="secondary" onClick={() => setStatusOpen(true)}>
                {suspended ? <Play className="h-4 w-4" /> : <Ban className="h-4 w-4" />}
                <span>{suspended ? 'Activate' : 'Suspend'}</span>
              </Button>
              <Button onClick={() => setBranchOpen(true)}>
                <Plus className="h-4 w-4" />
                <span>Add branch</span>
              </Button>
            </>
          ) : null
        }
      />

      {suspended ? (
        <p className="rounded-xl border border-danger/20 bg-danger-wash px-4 py-3 text-sm font-medium text-danger">
          This organization is suspended. Staff of all {org.clinics.length} clinics are blocked and their booking pages return not found.
        </p>
      ) : null}

      <Card className="p-5">
        <CardHeader
          title="Account"
          action={
            <Link href={`/audit-logs?organization_id=${org.id}`} className="text-xs font-semibold text-grove hover:text-grove-hover">
              Audit log for this organization
            </Link>
          }
        />
        <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Detail label="Type" value={ORGANIZATION_TYPE_LABEL[org.type]} />
          <Detail label="Billing contact email" value={org.contact_email ?? '-'} />
          <Detail label="Billing contact phone" value={org.contact_phone ?? '-'} />
          <Detail label="Customer since" value={formatDate(org.created_at)} />
        </dl>
      </Card>

      <div className="space-y-3">
        <h2 className="font-display text-[15.5px] font-bold text-ink">Clinics ({org.clinics.length})</h2>
        <DataTable
          columns={columns}
          data={org.clinics}
          emptyMessage="No clinics yet. Add the first branch."
          onRowClick={(c) => router.push(`/clinics/${c.id}`)}
        />
      </div>

      <ReasonActionSlideOver
        isOpen={statusOpen}
        onClose={() => setStatusOpen(false)}
        title={suspended ? 'Activate organization' : 'Suspend organization'}
        subtitle={org.name}
        tone={suspended ? 'default' : 'danger'}
        description={
          suspended ? (
            <>Clinics of this organization become usable again. Clinics that were suspended on their own stay suspended.</>
          ) : (
            <>
              All {org.clinics.length} clinics are blocked on their next request: staff cannot sign in or work, and booking pages return not
              found. No data is deleted.
            </>
          )
        }
        confirmLabel={suspended ? 'Activate' : 'Suspend organization'}
        isPending={setStatus.isPending}
        serverError={setStatus.isError ? errorMessage(setStatus.error) : null}
        onConfirm={(reason) =>
          setStatus.mutate(
            { action, reason },
            {
              onSuccess: () => {
                toast.success(suspended ? 'Organization activated' : 'Organization suspended');
                setStatusOpen(false);
                setStatus.reset();
              },
            },
          )
        }
      />

      <AddBranchSlideOver
        organizationId={org.id}
        organizationName={org.name}
        organizationSuspended={suspended}
        isOpen={branchOpen}
        onClose={() => setBranchOpen(false)}
      />
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="mt-1 break-words font-medium text-ink">{value}</dd>
    </div>
  );
}
