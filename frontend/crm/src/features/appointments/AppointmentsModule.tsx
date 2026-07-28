'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, Clock, QrCode, Plus, Check, X, Copy, MessageCircle } from 'lucide-react';
import {
  useAppointments,
  useCreateAppointment,
  useUpdateAppointmentStatus,
  useDeleteAppointment,
  useAppointmentRequests,
  useApproveRequest,
  useRejectRequest
} from './hooks/useAppointments';
import { AppointmentForm } from './components/AppointmentForm';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { useCRMStore } from '@/lib/store';
import { Appointment, AppointmentStatus } from '@/types/crm';
import { toast } from 'sonner';

export const AppointmentsModule: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'list' | 'requests' | 'booking'>('list');
  const [dateFilter, setDateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);

  const { data: appointments = [], isLoading, isError, refetch } = useAppointments();
  const createMutation = useCreateAppointment();
  const updateStatusMutation = useUpdateAppointmentStatus();
  const deleteMutation = useDeleteAppointment();

  const { data: requests = [], isLoading: isReqLoading } = useAppointmentRequests();
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();

  const { branding, therapists } = useCRMStore();

  const [approveReqId, setApproveReqId] = useState<string | null>(null);
  const [selectedTherapistId, setSelectedTherapistId] = useState(therapists[0]?.id || '');
  const [durationMinutes, setDurationMinutes] = useState(30);

  const pendingRequests = requests.filter((r) => r.status === 'Pending');

  const filteredAppts = appointments.filter((a) => {
    const matchesDate = dateFilter === '' || a.date === dateFilter;
    const matchesStatus = statusFilter === '' || a.status === statusFilter;
    return matchesDate && matchesStatus;
  });

  const handleBookAppt = (formData: any) => {
    createMutation.mutate(formData, {
      onSuccess: () => setIsAddOpen(false)
    });
  };

  const handleApproveConfirm = () => {
    if (approveReqId) {
      approveMutation.mutate(
        { id: approveReqId, therapistId: selectedTherapistId, duration: durationMinutes },
        { onSuccess: () => setApproveReqId(null) }
      );
    }
  };

  const handleWhatsApp = (mobile: string, name: string, time: string) => {
    const cleanMobile = mobile.replace(/\D/g, '');
    const num = cleanMobile.startsWith('91') ? cleanMobile : `91${cleanMobile}`;
    const msg = encodeURIComponent(
      `Hi ${name}, reminder for your confirmed physiotherapy slot today at ${time} with ${branding.clinicName}.`
    );
    window.open(`https://wa.me/${num}?text=${msg}`, '_blank');
  };

  const [lastLatency, setLastLatency] = useState('');
  useEffect(() => {
    setLastLatency(localStorage.getItem('api_last_latency') || '');
  }, [appointments]);

  return (
    <div className="space-y-6">
      {/* Sub-Tabs Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-2 text-xs font-bold uppercase tracking-wider">
        <button
          onClick={() => setActiveTab('list')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'list'
              ? 'border-[var(--teal)] text-[var(--teal)] font-extrabold'
              : 'border-transparent text-slate-400 hover:text-[var(--foreground)]'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Schedule List
        </button>

        <button
          onClick={() => setActiveTab('requests')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors relative ${
            activeTab === 'requests'
              ? 'border-[var(--teal)] text-[var(--teal)] font-extrabold'
              : 'border-transparent text-slate-400 hover:text-[var(--foreground)]'
          }`}
        >
          <Clock className="w-4 h-4" />
          Booking Requests Queue
          {pendingRequests.length > 0 && (
            <span className="px-2 py-0.5 text-[9px] bg-red-500 text-white font-extrabold rounded-full ml-1">
              {pendingRequests.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('booking')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'booking'
              ? 'border-[var(--teal)] text-[var(--teal)] font-extrabold'
              : 'border-transparent text-slate-400 hover:text-[var(--foreground)]'
          }`}
        >
          <QrCode className="w-4 h-4" />
          Public Link Generator
        </button>
      </div>

      {/* TAB 1: SCHEDULE LIST */}
      {activeTab === 'list' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C2541] text-xs font-bold"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C2541] text-xs font-bold"
              >
                <option value="">All Status</option>
                <option value="Scheduled">Scheduled</option>
                <option value="Confirmed">Confirmed</option>
                <option value="Completed">Completed</option>
                <option value="Cancelled">Cancelled</option>
                <option value="No Show">No Show</option>
              </select>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              {lastLatency && (
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">
                  ⚡ {lastLatency}
                </span>
              )}
              <button
                onClick={() => setIsAddOpen(true)}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-95 shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Book Slot
              </button>
            </div>
          </div>

          {isLoading ? (
            <LoadingSkeleton />
          ) : isError ? (
            <ErrorState onRetry={refetch} />
          ) : filteredAppts.length === 0 ? (
            <EmptyState
              title="No Appointments Scheduled"
              description="Schedule clinical treatment slots for patients, check lists, and track therapist assignments."
              actionLabel="Book First Slot"
              onAction={() => setIsAddOpen(true)}
            />
          ) : (
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-[#1C2541] shadow-sm">
              <table className="w-full text-left border-collapse text-xs clinical-table">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-slate-400">
                    <th className="p-4">Patient Name</th>
                    <th className="p-4">Date & Time</th>
                    <th className="p-4">Therapist</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50 text-[var(--foreground)]">
                  {filteredAppts.map((appt) => (
                    <tr key={appt.id} className="hover:bg-slate-50/40 dark:hover:bg-slate-900/10 transition-colors">
                      <td className="p-4 font-bold text-sm text-[var(--navy)] dark:text-[#48CAE4]">
                        {appt.patientName}
                      </td>
                      <td className="p-4 font-semibold">
                        {appt.date} at {appt.time} ({appt.durationMinutes} min)
                      </td>
                      <td className="p-4 text-slate-600 dark:text-slate-300">{appt.therapist || 'Unassigned'}</td>
                      <td className="p-4">
                        <span
                          className={`px-2.5 py-1 text-[10px] font-bold rounded-full border ${
                            appt.status === 'Completed'
                              ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                              : appt.status === 'Confirmed'
                              ? 'bg-blue-500/10 text-blue-650 border-blue-500/20'
                              : appt.status === 'Cancelled'
                              ? 'bg-red-500/10 text-red-500 border-red-500/20'
                              : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                          }`}
                        >
                          {appt.status}
                        </span>
                      </td>
                      <td className="p-4 text-right space-x-2">
                        <select
                          value=""
                          onChange={(e) => {
                            if (e.target.value) {
                              updateStatusMutation.mutate({ id: appt.id, status: e.target.value });
                            }
                          }}
                          className="px-2 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-[var(--background)] text-[var(--foreground)] font-semibold"
                        >
                          <option value="">Update...</option>
                          <option value="Confirmed">Confirmed</option>
                          <option value="Completed">Completed</option>
                          <option value="Cancelled">Cancelled</option>
                          <option value="No Show">No Show</option>
                        </select>
                        {appt.patientMobile && (
                          <button
                            onClick={() => handleWhatsApp(appt.patientMobile!, appt.patientName, appt.time)}
                            className="p-1.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors inline-flex items-center justify-center align-middle"
                            title="Send WhatsApp Reminder"
                          >
                            <MessageCircle className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(appt.id)}
                          className="text-red-500 hover:underline inline-block align-middle ml-2"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: BOOKING REQUESTS QUEUE */}
      {activeTab === 'requests' && (
        <div className="space-y-4">
          <div className="bg-[var(--card-bg)] border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm text-xs">
            <h3 className="font-bold text-sm text-[var(--foreground)]">Appointment Requests Queue</h3>
            <p className="text-slate-400 mt-0.5">
              Select and review booking slots submitted online by public patients.
            </p>
          </div>

          <div className="space-y-3">
            {pendingRequests.length === 0 ? (
              <EmptyState
                title="Requests Queue Empty"
                description="Patients requesting sessions via your public booking link will appear here for review."
              />
            ) : (
              pendingRequests.map((req) => (
                <div
                  key={req.id}
                  className="bg-[var(--card-bg)] border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <p className="font-bold text-sm text-[var(--foreground)]">{req.name}</p>
                    <p className="text-slate-400">
                      Mobile: {req.mobile} • Age/Gender: {req.age || '—'} / {req.gender || '—'}
                    </p>
                    <p className="font-semibold text-[var(--teal)]">
                      Preferred Date: {req.preferredDate} at {req.preferredTime}
                    </p>
                    {req.chiefComplaint && (
                      <p className="text-slate-400 italic">Complaint: "{req.chiefComplaint}"</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setApproveReqId(req.id)}
                      className="px-4 py-2 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-600 transition-colors inline-flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(req.id)}
                      className="px-4 py-2 bg-red-500 text-white font-bold rounded-lg hover:bg-red-650 transition-colors inline-flex items-center gap-1"
                    >
                      <X className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 3: PUBLIC LINK GENERATOR */}
      {activeTab === 'booking' && (
        <div className="max-w-xl space-y-6">
          <div className="bg-[var(--card-bg)] border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm space-y-4 text-xs">
            <h3 className="font-bold text-base text-[var(--foreground)]">Online Session Booking Link</h3>
            <p className="text-slate-400">
              Paste this URL in your bio or share it on WhatsApp. When patients book, requests go to the dashboard booking queue.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={branding.bookingUrl || 'https://aarogyavirohan.com/book'}
                className="flex-1 px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-[var(--background)] text-[var(--foreground)] font-mono text-xs focus:outline-none"
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(branding.bookingUrl || 'https://aarogyavirohan.com/book');
                  toast.success('Link copied to clipboard!');
                }}
                className="px-4 py-2.5 bg-[var(--teal)] text-white font-bold rounded-xl hover:opacity-95 inline-flex items-center gap-1"
              >
                <Copy className="w-3.5 h-3.5" />
                Copy
              </button>
            </div>

            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
              <h4 className="font-bold text-sm text-[var(--foreground)]">Printable QR Code</h4>
              <div className="p-4 bg-white rounded-2xl inline-block border border-slate-200">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(
                    branding.bookingUrl || 'https://aarogyavirohan.com/book'
                  )}`}
                  alt="Booking Form QR"
                  className="w-36 h-36"
                />
              </div>
              <p className="text-slate-400">
                Print and display this QR code at your reception desk or on clinic brochures.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Book Slot Modal */}
      {isAddOpen && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-lg p-6 space-y-4">
            <h3 className="text-base font-extrabold text-[var(--foreground)] border-b border-slate-100 dark:border-slate-800 pb-3">
              Book Appointment Slot
            </h3>
            <AppointmentForm onSubmit={handleBookAppt} onCancel={() => setIsAddOpen(false)} />
          </div>
        </div>
      )}

      {/* Approval Details Modal */}
      {approveReqId && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-md p-6 space-y-4 text-xs font-semibold">
            <h3 className="text-base font-extrabold text-[var(--foreground)]">Confirm Booking Details</h3>
            <p className="text-slate-400">Select the treating therapist and session duration for this patient.</p>

            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                Assigned Therapist
              </label>
              <select
                value={selectedTherapistId}
                onChange={(e) => setSelectedTherapistId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-[var(--background)] text-[var(--foreground)] text-sm font-semibold"
              >
                {therapists.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                Duration (minutes)
              </label>
              <input
                type="number"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-[var(--background)] text-[var(--foreground)] text-sm"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setApproveReqId(null)}
                className="px-4 py-2 border border-slate-200 dark:border-slate-800 rounded-lg text-[var(--foreground)] font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveConfirm}
                className="px-5 py-2 bg-emerald-500 text-white rounded-lg font-bold hover:bg-emerald-600 transition-colors"
              >
                Confirm Approval
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default AppointmentsModule;
