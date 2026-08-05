'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { useAuthStore } from '../../../store';
import { canAccessModule } from '../../../config/permissions';
import { UserRole } from '../../../types/api';
import { Trash2, RotateCcw, ShieldAlert } from 'lucide-react';
import { apiClient } from '../../../lib/api-client';
import { toast } from 'sonner';

interface DeletedItem {
  id: string;
  resource: 'patients' | 'leads' | 'appointments' | 'invoices' | 'patient_documents';
  name: string;
  deleted_at: string;
  deleted_by: string;
}

const MOCK_DELETED_ITEMS: DeletedItem[] = [
  {
    id: 'pat_99',
    resource: 'patients',
    name: 'Siddharth Rao (Patient)',
    deleted_at: '2026-08-01T10:00:00Z',
    deleted_by: 'admin@aarogya.com',
  },
  {
    id: 'lead_88',
    resource: 'leads',
    name: 'Neha Kapoor (Lead)',
    deleted_at: '2026-08-02T14:30:00Z',
    deleted_by: 'admin@aarogya.com',
  },
];

export default function RecycleBinPage() {
  const role = useAuthStore((s) => s.role) || ('admin' as UserRole);
  const [items, setItems] = useState<DeletedItem[]>(MOCK_DELETED_ITEMS);

  const handleRestore = async (resource: string, id: string) => {
    try {
      await apiClient.post(`/recycle-bin/${resource}/${id}/restore`);
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast.success('Item restored successfully');
    } catch (err) {
      console.warn('API unavailable, restoring mock item');
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast.success('Item restored successfully');
    }
  };

  if (!canAccessModule(role, 'recycleBin')) {
    return (
      <AppShell>
        <div className="p-8 max-w-md mx-auto text-center space-y-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          <ShieldAlert className="w-12 h-12 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Access Restricted</h2>
          <p className="text-xs text-slate-500">Recycle bin access is restricted to Administrators only.</p>
        </div>
      </AppShell>
    );
  }

  const columns: Column<DeletedItem>[] = [
    { key: 'name', header: 'Resource Item', render: (item) => <span className="font-bold">{item.name}</span> },
    { key: 'resource', header: 'Resource Type', render: (item) => <span className="uppercase text-xs font-semibold text-teal-600">{item.resource}</span> },
    { key: 'deleted_at', header: 'Deleted Date', render: (item) => new Date(item.deleted_at).toLocaleString() },
    { key: 'deleted_by', header: 'Deleted By' },
    {
      key: 'actions',
      header: 'Actions',
      render: (item) => (
        <button
          onClick={() => handleRestore(item.resource, item.id)}
          className="px-2.5 py-1 bg-teal-50 hover:bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300 rounded text-xs font-semibold flex items-center gap-1 cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Restore</span>
        </button>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Recycle Bin</h1>
          <p className="text-sm text-slate-500">View and restore soft-deleted clinic records (Admin only)</p>
        </div>

        <DataTable
          columns={columns}
          data={items}
          searchField={(i) => `${i.name} ${i.resource}`}
          searchPlaceholder="Search soft-deleted records..."
          emptyMessage="Recycle bin is empty."
        />
      </div>
    </AppShell>
  );
}
