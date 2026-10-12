'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { useAppointments, useUpdateAppointmentStatus } from '../../../features/appointments/api';
import { useClinicSettings } from '../../../features/settings/api';
import { AddAppointmentSlideOver } from '../../../features/appointments/components/AddAppointmentSlideOver';
import { RescheduleSlideOver } from '../../../features/appointments/components/RescheduleSlideOver';
import { WhatsAppButton } from '../../../components/ui/WhatsAppButton';
import { AppointmentStatus, Appointment } from '../../../types/api';
import { Plus, Calendar as CalendarIcon, Clock, CheckCircle2, XCircle, Copy, ExternalLink, QrCode, Phone } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { toast } from 'sonner';
import { apiClient } from '../../../lib/api-client';
import { useAuthStore } from '../../../store';
import { canAccessModule, canPerformAction, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { Avatar, Badge, type BadgeTone, Button, Card, PageHeader, SegmentGroup, SegmentTab } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

const STATUS_STYLE: Record<string, string> = {
  scheduled: 'bg-info-wash text-info border-info/20',
  completed: 'bg-ok-wash text-ok border-ok/20',
  cancelled: 'bg-danger-wash text-danger border-danger/20',
  no_show: 'bg-warn-wash text-warn border-warn/20',
};

const REQUEST_TONE: Record<BookingRequest['status'], BadgeTone> = {
  pending: 'warn',
  approved: 'ok',
  rejected: 'danger',
};

function apptDay(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(new Date(iso));
}

function apptTime(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso));
}

interface BookingRequest {
  id: string;
  name: string;
  phone: string;
  preferred_date: string;
  preferred_slot: string;
  chief_complaint: string;
  notes?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

type SubTabKey = 'list' | 'requests' | 'bookingLink';

export default function AppointmentsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const role = useAuthStore((s) => s.role);
  const isAllowed = canAccessModule('appointments');
  const { data: appointmentsResponse, isLoading } = useAppointments(undefined, undefined, 1, 10, isAllowed);
  const appointments: Appointment[] = appointmentsResponse?.data || [];
  const updateStatus = useUpdateAppointmentStatus();

  const [activeSubTab, setActiveSubTab] = useState<SubTabKey>('list');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [rescheduleAppointment, setRescheduleAppointment] = useState<Appointment | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | 'scheduled' | 'completed' | 'cancelled'>('all');
  const [requests, setRequests] = useState<BookingRequest[]>([]);

  const canViewBookingRequests = hasCapability('booking.view');

  // Fetch pending appointment requests from backend on mount (only for authorized roles)
  React.useEffect(() => {
    if (!canViewBookingRequests) return;
    const fetchRequests = async () => {
      try {
        const res = await apiClient.get('/appointment-requests');
        setRequests(res.data?.data || res.data || []);
      } catch {
        // If endpoint isn't live yet, stay empty rather than showing mock data
        setRequests([]);
      }
    };
    fetchRequests();
  }, [canViewBookingRequests]);

  // Booking link uses the clinic's UUID. The backend resolves a name-based
  // slug with a fuzzy name match, so a name link could open another clinic's
  // form (Decisions.md D-016). There is no fallback slug: until the clinic is
  // known, no link is shown.
  // The clinic from login is used first; settings are only read by roles that
  // may view them (staff got a 403 here, L-29).
  const authClinicId = useAuthStore((s) => s.clinic?.id ?? null);
  const { data: clinicSettings } = useClinicSettings(hasCapability('settings.view'));
  const bookingClinicId = authClinicId || clinicSettings?.id || null;
  const [bookingUrl, setBookingUrl] = useState<string | null>(null);
  React.useEffect(() => {
    if (bookingClinicId && typeof window !== 'undefined') {
      setBookingUrl(`${window.location.origin}/booking/${bookingClinicId}`);
    }
  }, [bookingClinicId]);
  const [showQr, setShowQr] = useState(false);

  const filteredAppointments = appointments.filter((apt) => {
    if (statusFilter !== 'all' && apt.status !== statusFilter) return false;
    return true;
  });

  if (!isAllowed) {
    return <AccessRestricted message="Appointments access is restricted for your role." />;
  }

  const handleStatusChange = async (id: string, newStatus: AppointmentStatus) => {
    try {
      await updateStatus.mutateAsync({ id, status: newStatus });
      toast.success('Appointment status updated');
    } catch (err) {
      console.error(err);
      toast.error('Failed to update status');
    }
  };

  const handleApproveRequest = async (req: BookingRequest) => {
    try {
      const userId = useAuthStore.getState().userId;
      await apiClient.post(`/appointment-requests/${req.id}/approve`, {
        therapist_id: userId || undefined,
        duration_minutes: 30,
      });

      // Refetch requests from backend to reflect actual state
      const res = await apiClient.get('/appointment-requests');
      setRequests(res.data?.data || res.data || []);
      toast.success(`Request approved! Appointment created for ${req.name}`);
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to approve request');
    }
  };

  const handleRejectRequest = async (req: BookingRequest) => {
    try {
      await apiClient.post(`/appointment-requests/${req.id}/reject`);

      // Refetch requests from backend to reflect actual state
      const res = await apiClient.get('/appointment-requests');
      setRequests(res.data?.data || res.data || []);
      toast.success(`Request rejected`);
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to reject request');
    }
  };

  const handleSaveBookingUrl = (url: string) => {
    // URL is now read-only and dynamically generated based on clinic name
  };

  const pendingRequestsCount = requests.filter((r) => r.status === 'pending').length;

  return (
    <AppShell>
      <div className="space-y-5">
        <PageHeader
          title="Appointments & Bookings"
          subtitle="Manage daily schedules & incoming public booking requests"
          actions={
            canPerformAction('manageAppointments') ? (
              <Button onClick={() => setIsAddOpen(true)}>
                <Plus className="h-4 w-4" />
                <span>Book Visit</span>
              </Button>
            ) : null
          }
        />

        {/* Sub-Tabs */}
        <SegmentGroup>
          <SegmentTab active={activeSubTab === 'list'} onClick={() => setActiveSubTab('list')} icon={CalendarIcon}>
            Appointments Schedule
          </SegmentTab>

          {canViewBookingRequests && (
            <SegmentTab active={activeSubTab === 'requests'} onClick={() => setActiveSubTab('requests')} icon={Clock}>
              Pending Requests
              {pendingRequestsCount > 0 && (
                <span className="rounded-full bg-danger px-2 py-0.5 text-[10px] font-extrabold text-white">
                  {pendingRequestsCount}
                </span>
              )}
            </SegmentTab>
          )}

          <SegmentTab active={activeSubTab === 'bookingLink'} onClick={() => setActiveSubTab('bookingLink')} icon={QrCode}>
            Public Booking Link & QR
          </SegmentTab>
        </SegmentGroup>

        {/* Sub-Tab 1: Appointments List */}
        {activeSubTab === 'list' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as 'all' | 'scheduled' | 'completed' | 'cancelled')}
                className="h-10 rounded-[10px] border border-line bg-card px-3 text-sm font-medium text-ink-2"
              >
                <option value="all">All Statuses</option>
                <option value="scheduled">Scheduled</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
                <option value="no_show">No Show</option>
              </select>
              <span className="text-xs text-muted">
                {filteredAppointments.length} {filteredAppointments.length === 1 ? 'appointment' : 'appointments'}
              </span>
            </div>

            {isLoading ? (
              <Card className="p-8 text-center text-sm text-muted">Loading appointments…</Card>
            ) : filteredAppointments.length === 0 ? (
              <Card className="p-10 text-center">
                <CalendarIcon className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-2 text-sm text-muted">No appointments found.</p>
              </Card>
            ) : (
              <Card className="divide-y divide-line-soft">
                {filteredAppointments.map((apt) => (
                  <div
                    key={apt.id}
                    className="flex flex-col items-start justify-between gap-4 px-5 py-4 md:flex-row md:items-center"
                  >
                    <div className="flex min-w-0 items-center gap-4">
                      <div className="w-[76px] shrink-0 rounded-xl bg-canvas px-2 py-2 text-center">
                        <p className="font-display text-lg font-bold leading-none tabular-nums text-ink">
                          {apptTime(apt.scheduled_at)}
                        </p>
                        <p className="mt-1 text-[11px] font-medium text-muted">{apptDay(apt.scheduled_at)}</p>
                      </div>
                      <Avatar name={apt.patient_name} size={40} />
                      <div className="min-w-0">
                        <h3 className="truncate text-[15px] font-semibold text-ink">
                          {apt.patient_name || `Patient ID: ${apt.patient_id}`}
                        </h3>
                        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {apt.duration_minutes} mins
                          </span>
                          {apt.therapist_name && (
                            <>
                              <span aria-hidden="true">·</span>
                              <span>{apt.therapist_name}</span>
                            </>
                          )}
                          {apt.appointment_type && (
                            <>
                              <span aria-hidden="true">·</span>
                              <span className="font-semibold capitalize text-logo-teal-ink">{apt.appointment_type}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex w-full items-center justify-between gap-2.5 md:w-auto md:justify-end">
                      <Button variant="secondary" className="h-9 px-3 text-xs" onClick={() => setRescheduleAppointment(apt)}>
                        <Clock className="h-3.5 w-3.5" />
                        <span>Reschedule</span>
                      </Button>
                      <select
                        value={apt.status}
                        onChange={(e) => handleStatusChange(apt.id, e.target.value as AppointmentStatus)}
                        aria-label="Appointment status"
                        className={cn(
                          'h-9 cursor-pointer rounded-[10px] border px-3 text-xs font-semibold',
                          STATUS_STYLE[apt.status] ?? 'border-line bg-card text-ink-2',
                        )}
                      >
                        <option value="scheduled">Scheduled</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="no_show">No Show</option>
                      </select>
                    </div>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}

        {/* Sub-Tab 2: Pending Booking Requests */}
        {activeSubTab === 'requests' && (
          <div className="space-y-3">
            <p className="text-xs text-muted">
              Incoming appointment requests from the public booking form. Approving auto-creates confirmed appointment & patient records.
            </p>

            {requests.length === 0 ? (
              <Card className="p-10 text-center">
                <Clock className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-2 text-sm text-muted">No public booking requests found.</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {requests.map((req) => (
                  <Card
                    key={req.id}
                    className="flex flex-col items-start justify-between gap-4 p-5 md:flex-row md:items-center"
                  >
                    <div className="flex min-w-0 gap-4">
                      <Avatar name={req.name} size={40} />
                      <div className="min-w-0 space-y-2">
                        <div className="flex items-center gap-2.5">
                          <h3 className="text-[15px] font-semibold text-ink">{req.name}</h3>
                          <Badge tone={REQUEST_TONE[req.status] ?? 'neutral'} className="capitalize">
                            {req.status}
                          </Badge>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted">
                          <span className="flex items-center gap-1">
                            <Phone className="h-3.5 w-3.5" />
                            <strong className="font-semibold text-ink-2">{req.phone}</strong>
                          </span>
                          <WhatsAppButton phone={req.phone} name={req.name} />
                          <span aria-hidden="true">·</span>
                          <span>
                            Service: <strong className="font-semibold text-ink-2">{req.notes ? req.notes.replace('Service Requested: ', '') : 'Consultation'}</strong>
                          </span>
                          <span aria-hidden="true">·</span>
                          <span>
                            Slot: <strong className="font-semibold text-ink-2">{req.preferred_date} at {req.preferred_slot}</strong>
                          </span>
                        </div>

                        <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-xs text-ink-2">
                          <strong className="font-semibold text-ink">Complaint:</strong> {req.chief_complaint}
                        </p>
                      </div>
                    </div>

                    {req.status === 'pending' && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleRejectRequest(req)}
                          className="flex h-9 cursor-pointer items-center gap-1.5 rounded-[10px] bg-danger-wash px-3 text-xs font-semibold text-danger transition-colors hover:bg-[#f7d6d1]"
                        >
                          <XCircle className="h-4 w-4" />
                          <span>Reject</span>
                        </button>
                        <Button className="h-9 px-3.5 text-xs" onClick={() => handleApproveRequest(req)}>
                          <CheckCircle2 className="h-4 w-4" />
                          <span>Approve & Book</span>
                        </Button>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sub-Tab 3: Public Booking Link & QR Code */}
        {activeSubTab === 'bookingLink' && (
          <Card className="max-w-2xl space-y-6 p-6">
            <div className="relative space-y-4 overflow-hidden rounded-2xl bg-[radial-gradient(90%_120%_at_100%_0%,#1d5a5a_0%,rgba(29,90,90,0)_55%),linear-gradient(135deg,#0b1238_0%,#13235a_60%,#1b4a54_100%)] p-6 text-white shadow-hero">
              <span
                aria-hidden="true"
                className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-gradient-to-br from-fresh to-[#0b665a] opacity-50"
              />
              <h3 className="relative text-lg font-bold">Public Appointment Booking Link</h3>
              <p className="relative text-xs text-[#c3c9e6]">
                Share this URL with patients on WhatsApp, Instagram bio, or print the QR Code for your clinic reception.
              </p>

              <div className="relative flex items-center gap-2">
                <input
                  type="text"
                  value={bookingUrl ?? 'Loading your booking link...'}
                  readOnly
                  aria-label="Public booking link"
                  className="flex-1 cursor-not-allowed rounded-[10px] border border-white/20 bg-white/10 px-3 py-2 text-xs text-white focus:outline-none"
                />
                <button
                  onClick={() => {
                    if (!bookingUrl) return;
                    navigator.clipboard.writeText(bookingUrl);
                    toast.success('Booking link copied to clipboard!');
                  }}
                  disabled={!bookingUrl}
                  className="flex cursor-pointer items-center gap-1.5 rounded-[10px] bg-lime px-3.5 py-2 text-xs font-bold text-midnight transition-colors hover:bg-[#d3ff9a] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy</span>
                </button>
                <a
                  href={bookingUrl ?? undefined}
                  aria-disabled={!bookingUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex cursor-pointer items-center gap-1 rounded-[10px] bg-white/15 px-3 py-2 text-xs font-bold text-white hover:bg-white/25"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Preview</span>
                </a>
              </div>
            </div>

            {/* QR Code Action */}
            <div className="space-y-4">
              <Button variant="secondary" onClick={() => setShowQr((prev) => !prev)}>
                <QrCode className="h-4 w-4" />
                <span>{showQr ? 'Hide QR Code' : 'Generate & Display QR Code'}</span>
              </Button>

              {showQr && bookingUrl && (
                <div className="flex items-center gap-6 rounded-2xl border border-line bg-canvas p-6">
                  <div className="flex h-32 w-32 items-center justify-center rounded-xl border border-line bg-white p-2 shadow-card">
                    <QRCodeCanvas value={bookingUrl} size={110} fgColor="#0b1238" />
                  </div>
                  <div className="space-y-1 text-xs text-muted">
                    <p className="text-sm font-bold text-ink">Scan to Book</p>
                    <p>Patients can scan this QR code with their mobile cameras to launch the public booking form directly.</p>
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Add Appointment Drawer */}
        <AddAppointmentSlideOver isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />

        {/* Reschedule Appointment Drawer */}
        <RescheduleSlideOver
          isOpen={!!rescheduleAppointment}
          onClose={() => setRescheduleAppointment(null)}
          appointment={rescheduleAppointment}
        />
      </div>
    </AppShell>
  );
}
