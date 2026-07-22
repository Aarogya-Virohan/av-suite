'use client';

import React, { useState } from 'react';
import { Search, Plus, User, Eye, Trash2, MessageCircle } from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { Patient, PatientStatus } from '@/types/crm';
import { PatientModal } from './PatientModal';
import { PatientDashboardModal } from './PatientDashboardModal';

export const PatientsView: React.FC = () => {
  const { patients, addPatient, updatePatient, deletePatient, branding } = useCRMStore();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [activeDashboardPatient, setActiveDashboardPatient] = useState<Patient | null>(null);

  const filteredPatients = patients.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.mobile.includes(searchTerm);
    const matchesStatus = statusFilter === '' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleSavePatient = (data: any) => {
    if (editingPatient) {
      updatePatient(editingPatient.id, data);
      setEditingPatient(null);
    } else {
      addPatient(data);
    }
  };

  const handleWhatsApp = (mobile: string, name: string) => {
    const cleanMobile = mobile.replace(/\D/g, '');
    const num = cleanMobile.startsWith('91') ? cleanMobile : `91${cleanMobile}`;
    const msg = encodeURIComponent(
      `Hi ${name}, greeting from ${branding.clinicName}. How can we assist with your recovery today?`
    );
    window.open(`https://wa.me/${num}?text=${msg}`, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-[var(--text-light)]" />
            <input
              type="text"
              placeholder="Search patients by name or mobile..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
          >
            <option value="">All Status</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
            <option value="Discharged">Discharged</option>
          </select>
        </div>

        <button
          onClick={() => {
            setEditingPatient(null);
            setIsAddModalOpen(true);
          }}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-sm font-bold rounded-xl hover:opacity-90 transition-opacity shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Add Patient
        </button>
      </div>

      {/* Patients Table */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] bg-gray-50/50 dark:bg-gray-800/30 text-[var(--text-light)] uppercase tracking-wider font-bold">
                <th className="p-4">Name</th>
                <th className="p-4">Mobile</th>
                <th className="p-4">Age / Gender</th>
                <th className="p-4">Diagnosis</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)] text-[var(--text)]">
              {filteredPatients.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-[var(--text-light)]">
                    No patients found matching your search criteria.
                  </td>
                </tr>
              ) : (
                filteredPatients.map((p) => (
                  <tr key={p.id} className="hover:bg-[var(--bg)] transition-colors">
                    <td className="p-4 font-bold text-sm text-[var(--navy)] dark:text-[var(--teal)]">
                      {p.name}
                    </td>
                    <td className="p-4">{p.mobile}</td>
                    <td className="p-4">
                      {p.age ? `${p.age} yrs` : '—'} / {p.gender || '—'}
                    </td>
                    <td className="p-4 max-w-xs truncate">{p.diagnosis || '—'}</td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-1 text-[11px] font-bold rounded-full ${
                          p.status === 'Active'
                            ? 'bg-emerald-500/15 text-emerald-600'
                            : p.status === 'Discharged'
                            ? 'bg-gray-500/15 text-gray-500'
                            : 'bg-amber-500/15 text-amber-600'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setActiveDashboardPatient(p)}
                          className="p-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--teal)] hover:text-white transition-colors"
                          title="Open Clinical Dashboard"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleWhatsApp(p.mobile, p.name)}
                          className="p-1.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                          title="Send WhatsApp Message"
                        >
                          <MessageCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deletePatient(p.id)}
                          className="p-1.5 rounded-lg border border-[var(--border)] text-red-500 hover:bg-red-500/10 transition-colors"
                          title="Move to Recycle Bin"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Patient Modal */}
      <PatientModal
        isOpen={isAddModalOpen || editingPatient !== null}
        onClose={() => {
          setIsAddModalOpen(false);
          setEditingPatient(null);
        }}
        onSave={handleSavePatient}
        patient={editingPatient}
      />

      {/* Clinical Patient Dashboard Modal */}
      <PatientDashboardModal
        patient={activeDashboardPatient}
        isOpen={activeDashboardPatient !== null}
        onClose={() => setActiveDashboardPatient(null)}
      />
    </div>
  );
};
