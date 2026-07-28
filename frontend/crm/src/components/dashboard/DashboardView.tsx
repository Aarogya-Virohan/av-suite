'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  Calendar,
  IndianRupee,
  Clock,
  UserCheck,
  BellRing,
  UserPlus,
  CalendarPlus,
  FileText,
  MessageCircle
} from 'lucide-react';
import { Chart as ChartJS, registerables } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { useCRMStore } from '@/lib/store';
import { NavTab } from '../layout/Sidebar';
import { useAnalyticsOverview } from '@/features/analytics/hooks/useAnalytics';
import { useAppointments, useAppointmentRequests } from '@/features/appointments/hooks/useAppointments';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

ChartJS.register(...registerables);

interface DashboardViewProps {
  onNavigate: (tab: NavTab) => void;
  onOpenPatientModal: () => void;
  onOpenApptModal: () => void;
  onOpenInvoiceModal: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
  onOpenPatientModal,
  onOpenApptModal,
  onOpenInvoiceModal
}) => {
  const { branding } = useCRMStore();

  const { data: analytics, isLoading: analyticsLoading, isError: analyticsError, refetch: refetchAnalytics } = useAnalyticsOverview();
  const { data: appointments = [], isLoading: apptsLoading, isError: apptsError, refetch: refetchAppts } = useAppointments();
  const { data: appointmentRequests = [] } = useAppointmentRequests();

  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const todayStr = new Date().toISOString().slice(0, 10);

  // Today's Appointments Count
  const todayAppts = appointments.filter((a: any) => a.date === todayStr);

  // Pending Requests Count
  const pendingRequests = appointmentRequests.filter((r: any) => r.status === 'Pending');

  const isLoading = analyticsLoading || apptsLoading;
  const isError = analyticsError || apptsError;
  const retryAll = () => {
    refetchAnalytics();
    refetchAppts();
  };

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <ErrorState onRetry={retryAll} />;

  // Safely get stats from analytics
  const todayApptsCount = analytics?.appointments.today_appointments || 0;
  const revenueThisMonth = analytics?.revenue.revenue_this_month || 0;
  const pendingPaymentsTotal = analytics?.revenue.total_outstanding_amount || 0;
  const activePatientsCount = analytics?.patients.active_patients || 0;



  const handleWhatsAppClick = (mobile: string, name: string) => {
    const cleanMobile = mobile.replace(/\D/g, '');
    const num = cleanMobile.startsWith('91') ? cleanMobile : `91${cleanMobile}`;
    const msg = encodeURIComponent(
      `Hi ${name}, reminder for your upcoming appointment at ${branding.clinicName}. For queries: ${branding.phone}`
    );
    window.open(`https://wa.me/${num}?text=${msg}`, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Pending Requests Alert Banner */}
      {pendingRequests.length > 0 && (
        <div
          onClick={() => onNavigate('appointments')}
          className="cursor-pointer bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-xl flex items-center justify-between transition-all hover:bg-red-500/15 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <BellRing className="w-6 h-6 animate-bounce" />
            <div>
              <p className="font-bold text-sm">
                {pendingRequests.length} New Booking Request{pendingRequests.length > 1 ? 's' : ''} Pending Approval
              </p>
              <p className="text-xs text-red-500/80">
                Click here to review and approve public form submissions
              </p>
            </div>
          </div>
          <span className="text-xs font-extrabold underline">Review Queue →</span>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
              Today's Appointments
            </span>
            <div className="p-2.5 rounded-lg bg-teal-500/15 text-teal-600">
              <Calendar className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-[var(--text)]">{todayApptsCount}</p>
          <p className="text-xs text-[var(--text-light)]">Scheduled for today</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
              Revenue This Month
            </span>
            <div className="p-2.5 rounded-lg bg-emerald-500/15 text-emerald-600">
              <IndianRupee className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-[var(--text)]">₹{revenueThisMonth.toLocaleString('en-IN')}</p>
          <p className="text-xs text-emerald-600 font-semibold">Collected this month</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
              Pending Payments
            </span>
            <div className="p-2.5 rounded-lg bg-amber-500/15 text-amber-600">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-[var(--text)]">
            ₹{pendingPaymentsTotal.toLocaleString('en-IN')}
          </p>
          <p className="text-xs text-amber-600 font-semibold">Outstanding invoices</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-light)] uppercase tracking-wider">
              Active Patients
            </span>
            <div className="p-2.5 rounded-lg bg-blue-500/15 text-blue-600">
              <UserCheck className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-[var(--text)]">{activePatientsCount}</p>
          <p className="text-xs text-[var(--text-light)]">Enrolled under care</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 className="font-bold text-base text-[var(--text)]">Revenue Trend (7 Days)</h3>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-xs font-semibold text-[var(--teal)] hover:underline"
            >
              Full Analytics →
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center p-4">
            <EmptyState
              title="Coming Soon"
              description="Revenue trend chart backend integration is pending."
              hideAction
            />
          </div>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 className="font-bold text-base text-[var(--text)]">Patient Growth</h3>
          </div>
          <div className="flex-1 flex items-center justify-center p-4">
            <EmptyState
              title="Coming Soon"
              description="Patient growth chart backend integration is pending."
              hideAction
            />
          </div>
        </div>
      </div>

      {/* Upcoming Appointments & Activity Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Appointments */}
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 className="font-bold text-base text-[var(--text)]">Upcoming Appointments</h3>
            <button
              onClick={() => onNavigate('appointments')}
              className="text-xs font-semibold text-[var(--teal)] hover:underline"
            >
              View All →
            </button>
          </div>

          <div className="space-y-3">
            {todayAppts.length === 0 ? (
              <p className="text-center py-6 text-xs text-[var(--text-light)]">
                No appointments scheduled for today
              </p>
            ) : (
              todayAppts.map((appt) => (
                <div
                  key={appt.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--bg)] hover:border-[var(--teal)] transition-colors"
                >
                  <div>
                    <p className="font-bold text-sm text-[var(--text)]">{appt.patient_name || appt.patientName}</p>
                    <p className="text-xs text-[var(--text-light)]">
                      {appt.time} • {appt.therapist_id || appt.therapist || 'Unassigned'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-teal-500/15 text-teal-600">
                      {appt.status}
                    </span>
                    {(appt.patient_mobile || appt.patientMobile) && (
                      <button
                        onClick={() => handleWhatsAppClick(appt.patient_mobile || appt.patientMobile, appt.patient_name || appt.patientName)}
                        className="p-1.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                        title="Send WhatsApp Reminder"
                      >
                        <MessageCircle className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Activity Timeline */}
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 className="font-bold text-base text-[var(--text)]">Recent Activity</h3>
          </div>

          <div className="space-y-3">
            <EmptyState
              title="Coming Soon"
              description="Audit logs backend integration is pending."
              hideAction
            />
          </div>
        </div>
      </div>

      {/* Quick Actions Bar */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-3">
        <h3 className="font-bold text-sm text-[var(--text)]">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={onOpenPatientModal}
            className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-[var(--navy)] text-white font-bold text-sm hover:opacity-90 transition-opacity shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            + Add Patient
          </button>
          <button
            onClick={onOpenApptModal}
            className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-[var(--teal)] text-white font-bold text-sm hover:opacity-90 transition-opacity shadow-sm"
          >
            <CalendarPlus className="w-4 h-4" />
            + Book Appointment
          </button>
          <button
            onClick={onOpenInvoiceModal}
            className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl border border-[var(--border)] text-[var(--text)] font-bold text-sm hover:bg-[var(--bg)] transition-colors shadow-sm"
          >
            <FileText className="w-4 h-4" />
            + Create Invoice
          </button>
        </div>
      </div>
    </div>
  );
};
