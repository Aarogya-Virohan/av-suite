'use client';

import React, { useState } from 'react';
import { Chart as ChartJS, registerables } from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { useAnalyticsOverview } from '@/features/analytics/hooks/useAnalytics';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';

ChartJS.register(...registerables);

export const AnalyticsView: React.FC = () => {
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month');
  const { data, isLoading, isError, refetch } = useAnalyticsOverview();

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (isError || !data) {
    return <ErrorState onRetry={refetch} />;
  }

  // Check if data is completely empty (no patients, no revenue, no appointments)
  if (data.patients.total_patients === 0 && data.revenue.revenue_this_month === 0) {
    return (
      <EmptyState
        title="No Analytics Data Available"
        description="There is currently no data in the system to generate analytics. Start by adding patients and booking appointments."
        actionLabel="Refresh Data"
        onAction={refetch}
      />
    );
  }

  const { patients, appointments, revenue, leads, booking } = data;

  // Doughnut: Appointments Status Breakdown
  const apptStatusData = {
    labels: ['Completed', 'Cancelled', 'No Show'],
    datasets: [
      {
        data: [appointments.completed_appointments, appointments.cancelled_appointments, appointments.no_show_appointments],
        backgroundColor: ['#22C55E', '#EF4444', '#F59E0B'],
        borderWidth: 0
      }
    ]
  };

  // Doughnut: Lead Sources
  const leadsByStageKeys = Object.keys(leads.leads_by_stage || {});
  const leadsByStageValues = Object.values(leads.leads_by_stage || {});

  const leadSourcesData = {
    labels: leadsByStageKeys.length > 0 ? leadsByStageKeys : ['No Data'],
    datasets: [
      {
        data: leadsByStageValues.length > 0 ? leadsByStageValues : [1],
        backgroundColor: ['#0B2C5F', '#1BB7B0', '#8B5CF6', '#22C55E', '#F59E0B', '#EF4444'],
        borderWidth: 0
      }
    ]
  };

  return (
    <div className="space-y-6">
      {/* Period Filter Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex bg-[var(--card-bg)] border border-[var(--border)] p-1 rounded-xl text-xs font-bold">
          {(['day', 'week', 'month', 'year'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-1.5 rounded-lg capitalize transition-colors ${
                period === p
                  ? 'bg-[var(--navy)] text-white shadow-sm'
                  : 'text-[var(--text-light)] hover:text-[var(--text)]'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <span className="text-xs text-[var(--text-light)] font-semibold">
          Filter Period: {period.toUpperCase()}
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Revenue Billed</p>
          <p className="text-lg font-extrabold text-[var(--teal)] mt-1">₹{Number(revenue.revenue_this_month).toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Outstanding</p>
          <p className="text-lg font-extrabold text-amber-500 mt-1">₹{Number(revenue.total_outstanding_amount).toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Active Patients</p>
          <p className="text-lg font-extrabold text-emerald-600 mt-1">{patients.active_patients}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Total Leads</p>
          <p className="text-lg font-extrabold text-indigo-500 mt-1">{leads.total_leads}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Appts Today</p>
          <p className="text-lg font-extrabold text-[var(--navy)] dark:text-white mt-1">{appointments.today_appointments}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Pending Bookings</p>
          <p className="text-lg font-extrabold text-red-500 mt-1">{booking.pending_requests}</p>
        </div>
      </div>

      {/* Doughnut Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <h4 className="font-bold text-sm text-[var(--text)]">Appointments Status</h4>
          <div className="h-56 flex items-center justify-center">
            <Doughnut data={apptStatusData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <h4 className="font-bold text-sm text-[var(--text)]">Leads By Stage</h4>
          <div className="h-56 flex items-center justify-center">
            <Doughnut data={leadSourcesData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>
      </div>
    </div>
  );
};
