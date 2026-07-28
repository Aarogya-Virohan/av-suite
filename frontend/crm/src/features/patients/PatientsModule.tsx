'use client';

import React, { useState, useEffect } from 'react';
import { Search, Plus } from 'lucide-react';
import {
  usePatients,
  useCreatePatient,
  useUpdatePatient,
  useDeletePatient
} from './hooks/usePatients';
import { PatientTable } from './components/PatientTable';
import { PatientForm } from './components/PatientForm';
import { PatientDashboardModal } from '@/components/patients/PatientDashboardModal';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Patient } from '@/types/crm';

export const PatientsModule: React.FC = () => {
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [selectedDashboardPt, setSelectedDashboardPt] = useState<Patient | null>(null);

  const { data: patients = [], isLoading, isError, refetch } = usePatients(page);
  const createMutation = useCreatePatient();
  const updateMutation = useUpdatePatient();
  const deleteMutation = useDeletePatient();

  const handleSavePatient = (formData: any) => {
    createMutation.mutate(formData, {
      onSuccess: () => setIsAddOpen(false)
    });
  };

  const handleWhatsApp = (mobile: string, name: string) => {
    const cleanMobile = mobile.replace(/\D/g, '');
    const num = cleanMobile.startsWith('91') ? cleanMobile : `91${cleanMobile}`;
    const msg = encodeURIComponent(
      `Hi ${name}, greeting from Aarogya Virohan. How is your physical rehab and recovery progressing today?`
    );
    window.open(`https://wa.me/${num}?text=${msg}`, '_blank');
  };

  const filteredPatients = patients.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.mobile.includes(searchTerm);
    const matchesStatus = statusFilter === '' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const [lastLatency, setLastLatency] = useState('');
  useEffect(() => {
    setLastLatency(localStorage.getItem('api_last_latency') || '');
  }, [patients]);

  return (
    <div className="space-y-6">
      {/* Page Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search patients by name or mobile..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C2541] text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C2541] text-xs font-bold focus:outline-none focus:border-[var(--teal)]"
          >
            <option value="">All Status</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
            <option value="Discharged">Discharged</option>
          </select>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {lastLatency && (
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 shrink-0">
              ⚡ {lastLatency}
            </span>
          )}
          <button
            onClick={() => setIsAddOpen(true)}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-95 transition-opacity shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add Patient
          </button>
        </div>
      </div>

      {/* Grid Content State Machine */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : filteredPatients.length === 0 ? (
        <EmptyState
          title="No Patients Enrolled"
          description="Enrolling patients allows clinical assessment logging, appointments scheduling, and prescription generation."
          actionLabel="Enroll First Patient"
          onAction={() => setIsAddOpen(true)}
        />
      ) : (
        <PatientTable
          patients={filteredPatients}
          onOpenDashboard={setSelectedDashboardPt}
          onWhatsApp={handleWhatsApp}
          onDelete={(id) => deleteMutation.mutate(id)}
        />
      )}

      {/* Intake Form Modal */}
      {isAddOpen && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-xl p-6 space-y-4">
            <h3 className="text-base font-extrabold text-[var(--foreground)] border-b border-slate-100 dark:border-slate-800 pb-3">
              Patient Clinical Intake
            </h3>
            <PatientForm onSubmit={handleSavePatient} onCancel={() => setIsAddOpen(false)} />
          </div>
        </div>
      )}

      {/* Clinical Dashboard Overlay */}
      <PatientDashboardModal
        patient={selectedDashboardPt}
        isOpen={selectedDashboardPt !== null}
        onClose={() => setSelectedDashboardPt(null)}
      />
    </div>
  );
};
export default PatientsModule;
