'use client';

import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  User,
  Plus,
  CheckCircle,
  XCircle,
  Copy,
  ExternalLink,
  QrCode,
  Check,
  X,
  MessageCircle
} from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { AppointmentStatus } from '@/types/crm';
import { openWhatsAppChat } from '@/lib/whatsapp';

export const AppointmentsView: React.FC<{ onOpenBookModal: () => void }> = ({
  onOpenBookModal
}) => {
  const [activeTab, setActiveTab] = useState<'list' | 'requests' | 'booking'>('list');
  const [dateFilter, setDateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const {
    appointments,
    updateAppointmentStatus,
    deleteAppointment,
    appointmentRequests,
    approveRequest,
    rejectRequest,
    branding,
    therapists
  } = useCRMStore();

  const [approveReqId, setApproveReqId] = useState<string | null>(null);
  const [selectedTherapistId, setSelectedTherapistId] = useState(therapists[0]?.id || '');
  const [durationMinutes, setDurationMinutes] = useState(30);

  const pendingRequests = appointmentRequests.filter((r) => r.status === 'Pending');

  const filteredAppts = appointments.filter((a) => {
    const matchesDate = dateFilter === '' || a.date === dateFilter;
    const matchesStatus = statusFilter === '' || a.status === statusFilter;
    return matchesDate && matchesStatus;
  });

  const handleApproveConfirm = () => {
    if (approveReqId) {
      approveRequest(approveReqId, selectedTherapistId, durationMinutes);
      setApproveReqId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub-tabs Header */}
      <div className="flex border-b border-[var(--border)] gap-2 text-sm font-bold">
        <button
          onClick={() => setActiveTab('list')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'list'
              ? 'border-[var(--teal)] text-[var(--teal)]'
              : 'border-transparent text-[var(--text-light)] hover:text-[var(--text)]'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Appointments Schedule
        </button>

        <button
          onClick={() => setActiveTab('requests')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors relative ${
            activeTab === 'requests'
              ? 'border-[var(--teal)] text-[var(--teal)]'
              : 'border-transparent text-[var(--text-light)] hover:text-[var(--text)]'
          }`}
        >
          <Clock className="w-4 h-4" />
          Booking Requests Queue
          {pendingRequests.length > 0 && (
            <span className="px-2 py-0.5 text-xs bg-red-500 text-white font-extrabold rounded-full">
              {pendingRequests.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('booking')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'booking'
              ? 'border-[var(--teal)] text-[var(--teal)]'
              : 'border-transparent text-[var(--text-light)] hover:text-[var(--text)]'
          }`}
        >
          <QrCode className="w-4 h-4" />
          Public Booking Link & QR
        </button>
      </div>

      {/* TAB 1: APPOINTMENTS SCHEDULE */}
      {activeTab === 'list' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-xs font-semibold focus:outline-none focus:border-[var(--teal)]"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] text-xs font-semibold focus:outline-none focus:border-[var(--teal)]"
              >
                <option value="">All Status</option>
                <option value="Scheduled">Scheduled</option>
                <option value="Confirmed">Confirmed</option>
                <option value="Completed">Completed</option>
                <option value="Cancelled">Cancelled</option>
                <option value="No Show">No Show</option>
              </select>
              {(dateFilter || statusFilter) && (
                <button
                  onClick={() => {
                    setDateFilter('');
                    setStatusFilter('');
                  }}
                  className="text-xs text-[var(--text-light)] underline hover:text-[var(--text)]"
                >
                  Clear Filters
                </button>
              )}
            </div>

            <button
              onClick={onOpenBookModal}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-90 transition-opacity shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Book Appointment
            </button>
          </div>

          {/* Schedule Table */}
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-gray-50/50 dark:bg-gray-800/30 text-[var(--text-light)] uppercase tracking-wider font-bold">
                    <th className="p-4">Patient</th>
                    <th className="p-4">Date & Time</th>
                    <th className="p-4">Therapist</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Update Status / Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] text-[var(--text)]">
                  {filteredAppts.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-[var(--text-light)]">
                        No appointments found matching your date or status filters.
                      </td>
                    </tr>
                  ) : (
                    filteredAppts.map((appt) => (
                      <tr key={appt.id} className="hover:bg-[var(--bg)] transition-colors">
                        <td className="p-4 font-bold text-sm text-[var(--navy)] dark:text-[var(--teal)]">
                          {appt.patientName}
                        </td>
                        <td className="p-4 font-semibold">
                          {appt.date} at {appt.time} ({appt.durationMinutes} min)
                        </td>
                        <td className="p-4">{appt.therapist || 'Unassigned'}</td>
                        <td className="p-4">
                          <span
                            className={`px-2.5 py-1 text-[11px] font-bold rounded-full ${
                              appt.status === 'Completed'
                                ? 'bg-emerald-500/15 text-emerald-600'
                                : appt.status === 'Confirmed'
                                ? 'bg-blue-500/15 text-blue-600'
                                : appt.status === 'Cancelled'
                                ? 'bg-red-500/15 text-red-500'
                                : 'bg-amber-500/15 text-amber-600'
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
                                updateAppointmentStatus(appt.id, e.target.value as AppointmentStatus);
                              }
                            }}
                            className="px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
                          >
                            <option value="">Update Status...</option>
                            <option value="Confirmed">Confirmed</option>
                            <option value="Completed">Completed</option>
                            <option value="Cancelled">Cancelled</option>
                            <option value="No Show">No Show</option>
                          </select>
                          <button
                            onClick={() => deleteAppointment(appt.id)}
                            className="text-red-500 hover:underline p-1"
                            title="Soft Delete"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: BOOKING REQUESTS QUEUE */}
      {activeTab === 'requests' && (
        <div className="space-y-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm">
            <h3 className="font-bold text-sm text-[var(--text)]">Public Form Submissions</h3>
            <p className="text-xs text-[var(--text-light)] mt-0.5">
              Approving a request creates a Confirmed Appointment, auto-creates the Patient record, and auto-adds a Lead.
            </p>
          </div>

          <div className="space-y-3">
            {appointmentRequests.length === 0 ? (
              <p className="text-center py-8 text-xs text-[var(--text-light)] bg-[var(--card-bg)] rounded-xl border border-[var(--border)]">
                No booking requests submitted yet.
              </p>
            ) : (
              appointmentRequests.map((req) => (
                <div
                  key={req.id}
                  className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[var(--text)]">{req.name}</span>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                          req.status === 'Approved'
                            ? 'bg-emerald-500/15 text-emerald-600'
                            : req.status === 'Rejected'
                            ? 'bg-red-500/15 text-red-500'
                            : 'bg-amber-500/15 text-amber-600'
                        }`}
                      >
                        {req.status}
                      </span>
                    </div>
                    <p className="text-[var(--text-light)]">
                      Mobile: {req.mobile} • Age/Gender: {req.age || '—'} / {req.gender || '—'}
                    </p>
                    <p className="font-semibold text-[var(--teal)]">
                      Preferred Date: {req.preferredDate} at {req.preferredTime}
                    </p>
                    {req.chiefComplaint && (
                      <p className="text-[var(--text-light)] italic">Complaint: {req.chiefComplaint}</p>
                    )}
                  </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          const msg = `Hello ${req.name}, your booking request for ${req.preferredDate} at ${req.preferredTime} at ${branding.clinicName} has been confirmed. Thank you!`;
                          openWhatsAppChat(req.mobile || '', msg);
                        }}
                        className="px-3 py-2 bg-emerald-600/10 border border-emerald-500/30 text-emerald-600 text-xs font-bold rounded-lg hover:bg-emerald-600/20 transition-colors inline-flex items-center gap-1.5"
                        title="Send confirmation via WhatsApp"
                      >
                        <MessageCircle className="w-3.5 h-3.5" />
                        WhatsApp
                      </button>
                      {req.status === 'Pending' && (
                        <>
                          <button
                            onClick={() => setApproveReqId(req.id)}
                            className="px-4 py-2 bg-emerald-500 text-white text-xs font-bold rounded-lg hover:bg-emerald-600 transition-colors inline-flex items-center gap-1"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Approve
                          </button>
                          <button
                            onClick={() => rejectRequest(req.id)}
                            className="px-4 py-2 bg-red-500 text-white text-xs font-bold rounded-lg hover:bg-red-600 transition-colors inline-flex items-center gap-1"
                          >
                            <X className="w-3.5 h-3.5" />
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 3: PUBLIC BOOKING LINK & QR CODE */}
      {activeTab === 'booking' && (
        <div className="space-y-6 max-w-2xl">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] p-6 rounded-xl shadow-sm space-y-4 text-xs">
            <h3 className="font-bold text-base text-[var(--text)]">Public Patient Booking Link</h3>
            <p className="text-[var(--text-light)]">
              Share this link with patients via WhatsApp or Instagram. Patients can request appointment slots directly.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={branding.bookingUrl || 'https://aarogyavirohan.com/book'}
                className="flex-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-mono text-xs"
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(branding.bookingUrl || 'https://aarogyavirohan.com/book');
                  alert('Booking URL copied to clipboard!');
                }}
                className="px-4 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90 inline-flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" />
                Copy Link
              </button>
            </div>

            <div className="pt-4 border-t border-[var(--border)] space-y-3">
              <h4 className="font-bold text-sm text-[var(--text)]">QR Code for Print / Clinic Banner</h4>
              <div className="p-4 bg-white rounded-xl inline-block border border-gray-200">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(
                    branding.bookingUrl || 'https://aarogyavirohan.com/book'
                  )}`}
                  alt="Booking QR Code"
                  className="w-40 h-40"
                />
              </div>
              <p className="text-[var(--text-light)]">
                Scan with phone camera to open online booking form instantly.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Approve Request Modal */}
      {approveReqId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl p-6 w-full max-w-md space-y-4 text-xs">
            <h3 className="font-bold text-base text-[var(--text)]">Approve Booking Request</h3>
            <p className="text-[var(--text-light)]">
              Approving will create a confirmed appointment slot and patient profile.
            </p>

            <div>
              <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Assigned Therapist</label>
              <select
                value={selectedTherapistId}
                onChange={(e) => setSelectedTherapistId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] font-semibold"
              >
                {therapists.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Duration (Minutes)</label>
              <input
                type="number"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setApproveReqId(null)}
                className="px-4 py-2 border border-[var(--border)] rounded-lg text-[var(--text)] font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveConfirm}
                className="px-4 py-2 bg-emerald-500 text-white rounded-lg font-bold hover:bg-emerald-600"
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
