'use client';

import React, { useState } from 'react';
import { Sidebar, NavTab } from '@/components/layout/Sidebar';
import { Topbar } from '@/components/layout/Topbar';
import { DashboardView } from '@/components/dashboard/DashboardView';
import { AnalyticsView } from '@/components/analytics/AnalyticsView';
import { PatientsModule } from '@/features/patients/PatientsModule';
import { AppointmentsModule } from '@/features/appointments/AppointmentsModule';
import { BillingView } from '@/components/billing/BillingView';
import { LeadsView } from '@/components/leads/LeadsView';
import { TherapistsView } from '@/components/therapists/TherapistsView';
import { RecycleBinView } from '@/components/recycle/RecycleBinView';
import { SettingsView } from '@/components/settings/SettingsView';
import { PatientModal } from '@/components/patients/PatientModal';
import { InvoiceModal } from '@/components/billing/InvoiceModal';
import { useCRMStore } from '@/lib/store';
import { X } from 'lucide-react';

export default function CRMApp() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Global Modal States
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false);
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false);
  const [isApptModalOpen, setIsApptModalOpen] = useState(false);

  // Form State for Quick Book Appointment Modal
  const { patients, therapists, addAppointment, addPatient } = useCRMStore();
  const [apptPtId, setApptPtId] = useState(patients[0]?.id || '');
  const [apptDate, setApptDate] = useState(new Date().toISOString().slice(0, 10));
  const [apptTime, setApptTime] = useState('10:30');
  const [apptTherapist, setApptTherapist] = useState(therapists[0]?.name || '');
  const [apptNotes, setApptNotes] = useState('');

  const handleRefresh = () => {
    // Re-trigger render
  };

  const handleBookApptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const pt = patients.find((p) => p.id === apptPtId);
    if (!pt) {
      alert('Please select a patient.');
      return;
    }
    addAppointment({
      patientId: pt.id,
      patientName: pt.name,
      patientMobile: pt.mobile,
      therapist: apptTherapist,
      date: apptDate,
      time: apptTime,
      durationMinutes: 30,
      status: 'Confirmed',
      source: 'manual',
      notes: apptNotes.trim() || undefined
    });
    setIsApptModalOpen(false);
    setApptNotes('');
  };

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--text)] transition-colors duration-200">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 md:ml-64 flex flex-col min-w-0">
        <Topbar
          activeTab={activeTab}
          onOpenMenu={() => setIsMobileMenuOpen(true)}
          onRefresh={handleRefresh}
        />

        <main className="p-4 sm:p-8 flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <DashboardView
              onNavigate={setActiveTab}
              onOpenPatientModal={() => setIsPatientModalOpen(true)}
              onOpenApptModal={() => setIsApptModalOpen(true)}
              onOpenInvoiceModal={() => setIsInvoiceModalOpen(true)}
            />
          )}

          {activeTab === 'analytics' && <AnalyticsView />}

          {activeTab === 'patients' && <PatientsModule />}

          {activeTab === 'appointments' && <AppointmentsModule />}

          {activeTab === 'billing' && (
            <BillingView onOpenInvoiceModal={() => setIsInvoiceModalOpen(true)} />
          )}

          {activeTab === 'leads' && <LeadsView />}

          {activeTab === 'therapists' && <TherapistsView />}

          {activeTab === 'recycle' && <RecycleBinView />}

          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>

      {/* Global Add Patient Modal */}
      <PatientModal
        isOpen={isPatientModalOpen}
        onClose={() => setIsPatientModalOpen(false)}
        onSave={(data) => addPatient(data)}
      />

      {/* Global Create Invoice Modal */}
      <InvoiceModal
        isOpen={isInvoiceModalOpen}
        onClose={() => setIsInvoiceModalOpen(false)}
      />

      {/* Global Book Appointment Modal */}
      {isApptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <h2 className="text-lg font-bold text-[var(--text)]">Book Appointment</h2>
              <button onClick={() => setIsApptModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleBookApptSubmit} className="space-y-4">
              <div>
                <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Select Patient *</label>
                <select
                  value={apptPtId}
                  onChange={(e) => setApptPtId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
                  required
                >
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.mobile})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Date *</label>
                  <input
                    type="date"
                    value={apptDate}
                    onChange={(e) => setApptDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
                    required
                  />
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Time *</label>
                  <input
                    type="time"
                    value={apptTime}
                    onChange={(e) => setApptTime(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Assigned Therapist</label>
                <select
                  value={apptTherapist}
                  onChange={(e) => setApptTherapist(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
                >
                  {therapists.map((t) => (
                    <option key={t.id} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Appointment Notes</label>
                <textarea
                  value={apptNotes}
                  onChange={(e) => setApptNotes(e.target.value)}
                  placeholder="Treatment goals, chief complaint..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsApptModalOpen(false)}
                  className="px-4 py-2 border border-[var(--border)] rounded-lg text-[var(--text)] font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90"
                >
                  Confirm Booking
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
