'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { usePatients } from '../../../features/patients/api';
import { AddPatientSlideOver } from '../../../features/patients/components/AddPatientSlideOver';
import { WhatsAppButton } from '../../../components/ui/WhatsAppButton';
import { Patient, PatientStatus } from '../../../types/api';
import { Plus, Phone } from 'lucide-react';
import { canAccessModule, canPerformAction, usePermissionSubscription } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { Avatar, Badge, type BadgeTone, Button, PageHeader, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

const STATUS_TONE: Record<PatientStatus, BadgeTone> = {
  active: 'ok',
  inactive: 'neutral',
  discharged: 'info',
};

/*
 * Restyled to the AV Suite theme. Also fixed:
 * - Each row printed the full patient UUID under the name.
 * - The status filter used to filter only the loaded page (L-33). The API
 *   now filters by status, so the filter covers the whole list and the
 *   pagination counts match it.
 */
export default function PatientsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const isAllowed = canAccessModule('patients');
  const [statusFilter, setStatusFilter] = useState<PatientStatus | 'all'>('all');
  const { data: response, isLoading } = usePatients(
    searchTerm,
    page,
    pageSize,
    isAllowed,
    statusFilter === 'all' ? undefined : statusFilter,
  );
  const patients = response?.data || [];
  const meta = response?.meta;
  const [isAddOpen, setIsAddOpen] = useState(false);

  if (!isAllowed) {
    // AccessRestricted renders its own AppShell.
    return <AccessRestricted message="Patients directory access is restricted for your role." />;
  }

  const columns: Column<Patient>[] = [
    {
      key: 'name',
      header: 'Patient Name',
      render: (patient) => (
        <div className="flex items-center gap-3">
          <Avatar name={`${patient.first_name} ${patient.last_name}`} size={34} />
          <p className="min-w-0 truncate font-semibold text-ink">
            {patient.first_name} {patient.last_name}
          </p>
        </div>
      ),
    },
    {
      key: 'phone',
      header: 'Phone Number',
      render: (patient) => (
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-ink-2 tabular-nums">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            {patient.phone}
          </span>
          <WhatsAppButton phone={patient.phone} name={`${patient.first_name} ${patient.last_name}`} />
        </div>
      ),
    },
    {
      key: 'chief_complaint',
      header: 'Chief Complaint',
      render: (patient) => <span className="line-clamp-1 text-xs text-ink-2">{patient.chief_complaint}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (patient) => (
        <Badge tone={STATUS_TONE[patient.status] ?? 'neutral'} className="capitalize">
          {patient.status}
        </Badge>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Patients Directory"
          subtitle="Manage patient records & clinical workspaces"
          actions={
            <>
              <select
                aria-label="Filter by status"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as PatientStatus | 'all');
                  setPage(1); // a new filter starts on page 1
                }}
                className={cn(inputClass, 'w-auto')}
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="discharged">Discharged</option>
              </select>

              {canPerformAction('createEditPatient') && (
                <Button onClick={() => setIsAddOpen(true)}>
                  <Plus className="h-4 w-4" />
                  <span>Add Patient</span>
                </Button>
              )}
            </>
          }
        />

        <DataTable
          columns={columns}
          data={patients}
          isLoading={isLoading}
          onSearchChange={(term) => {
            setSearchTerm(term);
            setPage(1); // Reset to page 1 on new search
          }}
          searchPlaceholder="Search by patient name or phone number..."
          emptyMessage={statusFilter !== 'all' ? `No ${statusFilter} patients found.` : 'No patients found.'}
          onRowClick={(patient) => router.push(`/patients/${patient.id}`)}
          totalItems={meta?.total}
          currentPage={meta?.page}
          pageSize={meta?.page_size}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />

        <AddPatientSlideOver isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />
      </div>
    </AppShell>
  );
}
