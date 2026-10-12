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
 * - The restricted state rendered without the app shell (no sidebar).
 * - Each row printed the full patient UUID under the name.
 * - The status filter only filters the page that is loaded (the API has no
 *   status filter, Decisions.md L-33). The empty message now says so instead
 *   of implying there are no such patients at all.
 */
export default function PatientsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const isAllowed = canAccessModule('patients');
  const { data: response, isLoading } = usePatients(searchTerm, page, 10, isAllowed);
  const patients = response?.data || [];
  const meta = response?.meta;
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredPatients = patients.filter((p) => {
    if (statusFilter === 'all') return true;
    return p.status === statusFilter;
  });

  if (!isAllowed) {
    return (
      <AppShell>
        <AccessRestricted message="Patients directory access is restricted for your role." />
      </AppShell>
    );
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
                onChange={(e) => setStatusFilter(e.target.value)}
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
          data={filteredPatients}
          isLoading={isLoading}
          onSearchChange={(term) => {
            setSearchTerm(term);
            setPage(1); // Reset to page 1 on new search
          }}
          searchPlaceholder="Search by patient name or phone number..."
          emptyMessage={
            statusFilter !== 'all' && patients.length > 0
              ? `No ${statusFilter} patients on this page.`
              : 'No patients found.'
          }
          onRowClick={(patient) => router.push(`/patients/${patient.id}`)}
          totalItems={meta?.total}
          currentPage={meta?.page}
          pageSize={meta?.page_size}
          onPageChange={setPage}
        />

        <AddPatientSlideOver isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />
      </div>
    </AppShell>
  );
}
