'use client';

import React, { useState } from 'react';
import { Terminal, UserCog, UserMinus, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { ReasonActionSlideOver } from '@/components/forms/ReasonActionSlideOver';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { Avatar, Badge, Button, Card, PageHeader } from '@/components/ui/brand';
import { ErrorCard } from '@/components/ui/ErrorCard';
import { ChangeRoleSlideOver } from '@/features/operators/ChangeRoleSlideOver';
import { useOperators, useUpdateOperator } from '@/features/operators/hooks';
import { formatRelative, OPERATOR_ROLE_LABEL } from '@/lib/format';
import { errorMessage } from '@/lib/platform-api/errors';
import { UI_PAGE_SIZE, type Operator } from '@/lib/platform-api/types';
import { useSession } from '@/store/session';

export default function OperatorsPage() {
  return (
    <RequirePermission permission="platform.operators.manage">
      <Operators />
    </RequirePermission>
  );
}

function Operators() {
  const me = useSession((s) => s.operator);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(UI_PAGE_SIZE);
  const query = useOperators({ page, page_size: pageSize });
  const update = useUpdateOperator();
  const [roleTarget, setRoleTarget] = useState<Operator | null>(null);
  const [activeTarget, setActiveTarget] = useState<Operator | null>(null);

  const columns: Column<Operator>[] = [
    {
      key: 'name',
      header: 'Operator',
      render: (o) => (
        <div className="flex items-center gap-3">
          <Avatar name={o.name} size={32} />
          <div className="min-w-0">
            <p className="truncate font-semibold text-ink">
              {o.name}
              {o.id === me?.id ? <span className="font-normal text-muted"> (you)</span> : null}
            </p>
            <p className="truncate text-xs text-muted">{o.email}</p>
          </div>
        </div>
      ),
    },
    { key: 'role', header: 'Role', render: (o) => <Badge tone={o.role === 'owner' ? 'active' : 'info'}>{OPERATOR_ROLE_LABEL[o.role]}</Badge> },
    {
      key: 'mfa',
      header: 'Two-step',
      render: (o) => (o.mfa_enabled ? <Badge tone="ok">Enrolled</Badge> : <Badge tone="warn">Pending first login</Badge>),
    },
    { key: 'status', header: 'Status', render: (o) => (o.is_active ? <Badge tone="ok">Active</Badge> : <Badge tone="neutral">Deactivated</Badge>) },
    { key: 'last_login_at', header: 'Last sign-in', render: (o) => formatRelative(o.last_login_at) },
    {
      key: 'actions',
      header: '',
      render: (o) =>
        o.role === 'owner' ? (
          // P-7: the Owner set changes only through the CLI; the backend answers 403 too.
          <div className="flex items-center justify-end gap-1.5" title="Owner changes via CLI only">
            <Button variant="ghost" className="h-8 px-3" disabled aria-label={`Change role of ${o.name} (Owner changes via CLI only)`}>
              <UserCog className="h-3.5 w-3.5" />
              <span>Role</span>
            </Button>
            <Button variant="ghost" className="h-8 px-3" disabled aria-label={`Deactivate ${o.name} (Owner changes via CLI only)`}>
              <UserMinus className="h-3.5 w-3.5" />
              <span>Deactivate</span>
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" className="h-8 px-3" onClick={() => setRoleTarget(o)} disabled={!o.is_active}>
              <UserCog className="h-3.5 w-3.5" />
              <span>Role</span>
            </Button>
            <Button variant="ghost" className="h-8 px-3" onClick={() => setActiveTarget(o)}>
              {o.is_active ? <UserMinus className="h-3.5 w-3.5" /> : <UserPlus className="h-3.5 w-3.5" />}
              <span>{o.is_active ? 'Deactivate' : 'Reactivate'}</span>
            </Button>
          </div>
        ),
    },
  ];

  const deactivating = activeTarget?.is_active ?? false;

  return (
    <div className="space-y-6">
      <PageHeader title="Operators" subtitle="AV team accounts for this console. Owners only." />

      <Card className="flex items-start gap-3 p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-logo-teal-wash text-logo-teal">
          <Terminal className="h-[18px] w-[18px]" strokeWidth={1.8} />
        </span>
        <div className="text-sm text-ink-2">
          <p className="font-semibold text-ink">Operators are created via CLI by an Owner</p>
          <p className="mt-1">
            Run <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-ink">python -m app.scripts.create_platform_operator</code>{' '}
            on the backend. The console never sets passwords; a new operator enrols two-step sign-in on first login. Owner changes
            (role, deactivation) are CLI only too.
          </p>
        </div>
      </Card>

      {query.isError ? (
        <ErrorCard message={errorMessage(query.error, 'Could not load operators.')} onRetry={() => query.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={query.data?.data ?? []}
          isLoading={query.isLoading}
          emptyMessage="No operators."
          totalItems={query.data?.meta.total ?? 0}
          currentPage={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      )}

      <ChangeRoleSlideOver operator={roleTarget} onClose={() => setRoleTarget(null)} />

      <ReasonActionSlideOver
        isOpen={activeTarget !== null}
        onClose={() => setActiveTarget(null)}
        title={deactivating ? 'Deactivate operator' : 'Reactivate operator'}
        subtitle={activeTarget?.name}
        tone={deactivating ? 'danger' : 'default'}
        description={
          deactivating ? (
            <>They are signed out of every session on their next request and cannot sign in again until an Owner reactivates them.</>
          ) : (
            <>They can sign in again with their existing password and authenticator app.</>
          )
        }
        confirmLabel={deactivating ? 'Deactivate' : 'Reactivate'}
        isPending={update.isPending}
        serverError={update.isError ? errorMessage(update.error) : null}
        onConfirm={(reason) => {
          if (!activeTarget) return;
          update.mutate(
            { id: activeTarget.id, body: { is_active: !activeTarget.is_active, reason } },
            {
              onSuccess: (o) => {
                toast.success(o.is_active ? `${o.name} reactivated` : `${o.name} deactivated`);
                setActiveTarget(null);
                update.reset();
              },
            },
          );
        }}
      />
    </div>
  );
}
