'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { RotateCcw, AlertTriangle } from 'lucide-react';
import { apiClient } from '../../../lib/api-client';
import { toast } from 'sonner';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { Badge, type BadgeTone, Card, PageHeader } from '../../../components/ui/brand';
import { useUsers } from '../../../features/users/api';
import type { components } from '../../../types/schema';

/**
 * Typed from the generated API schema. The old local interface expected
 * `name` and `resource`, but the backend sends `title` and `resource_type`,
 * so names rendered blank and Restore called /recycle-bin/undefined/...
 */
type DeletedItem = components['schemas']['RecycleBinItemResponse'];

const TYPE_TONE: Record<string, BadgeTone> = {
  patient: 'active',
  lead: 'info',
  appointment: 'warn',
  invoice: 'ok',
  document: 'neutral',
};

const deletedAtFormat = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

function formatDeletedAt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : deletedAtFormat.format(date);
}

export default function RecycleBinPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const hasAccess = canAccessModule('recycleBin');
  const canRestore = hasCapability('recyclebin.restore');
  const canViewUsers = hasCapability('users.view');

  const [items, setItems] = useState<DeletedItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  const { data: users = [] } = useUsers(hasAccess && canViewUsers);

  React.useEffect(() => {
    if (!hasAccess) return;
    let cancelled = false;
    const fetchDeletedItems = async () => {
      setIsLoading(true);
      try {
        const res = await apiClient.get('/recycle-bin');
        const data = res.data?.items ?? res.data?.data?.items ?? res.data?.data ?? res.data;
        if (!cancelled) {
          setItems(Array.isArray(data) ? data : []);
          setLoadError(false);
        }
      } catch {
        // Show the failure instead of pretending the bin is empty.
        if (!cancelled) {
          setItems([]);
          setLoadError(true);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    fetchDeletedItems();
    return () => {
      cancelled = true;
    };
  }, [hasAccess]);

  const handleRestore = async (item: DeletedItem) => {
    setRestoringId(item.id);
    try {
      await apiClient.post(`/recycle-bin/${item.resource_type}/${item.id}/restore`);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      toast.success(`${item.title} restored successfully`);
    } catch {
      toast.error('Failed to restore item');
    } finally {
      setRestoringId(null);
    }
  };

  if (!hasAccess) {
    // AccessRestricted renders its own AppShell.
    return <AccessRestricted message="Recycle bin access is restricted." />;
  }

  const deletedByName = (userId: string | null | undefined) => {
    if (!userId) return '-';
    const u = users.find((user) => user.id === userId);
    return u ? `${u.first_name} ${u.last_name}` : `User #${userId.slice(0, 8).toUpperCase()}`;
  };

  const columns: Column<DeletedItem>[] = [
    { key: 'title', header: 'Item', render: (item) => <span className="font-semibold text-ink">{item.title}</span> },
    {
      key: 'resource_type',
      header: 'Type',
      render: (item) => (
        <Badge tone={TYPE_TONE[item.resource_type] ?? 'neutral'} className="capitalize">
          {item.resource_type}
        </Badge>
      ),
    },
    {
      key: 'deleted_at',
      header: 'Deleted',
      render: (item) => <span className="tabular-nums">{formatDeletedAt(item.deleted_at)}</span>,
    },
    { key: 'deleted_by', header: 'Deleted By', render: (item) => deletedByName(item.deleted_by) },
    ...(canRestore
      ? [
          {
            key: 'actions',
            header: 'Actions',
            render: (item: DeletedItem) => (
              <button
                onClick={() => handleRestore(item)}
                disabled={restoringId === item.id}
                className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg bg-grove-wash px-2.5 text-xs font-semibold text-grove transition-colors hover:bg-[#d3eedc] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>{restoringId === item.id ? 'Restoring...' : 'Restore'}</span>
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader title="Recycle Bin" subtitle="View and restore soft-deleted clinic records" />

        {loadError ? (
          <Card role="alert" className="flex items-center gap-3 border-danger/30 bg-danger-wash p-4 text-sm font-medium text-danger">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Unable to load the recycle bin. Refresh the page or try again later.
          </Card>
        ) : (
          <DataTable
            columns={columns}
            data={items}
            isLoading={isLoading}
            searchField={(i) => `${i.title} ${i.resource_type}`}
            searchPlaceholder="Search deleted records..."
            emptyMessage="Recycle bin is empty."
          />
        )}
      </div>
    </AppShell>
  );
}
