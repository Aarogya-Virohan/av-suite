'use client';

import React from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { Users, Calendar, DollarSign, UserCheck, Loader2 } from 'lucide-react';
import { useAnalyticsOverview } from '../../../features/analytics/api';
import { useAuthStore } from '../../../store';
import { canAccessModule } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';

export default function DashboardPage() {
  const role = useAuthStore((s) => s.role);
  const { data: overview, isLoading, isError, error } = useAnalyticsOverview();

  if (!canAccessModule(role, 'dashboard')) {
    return <AccessRestricted message="Dashboard access is restricted." />;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Welcome back to Aarogya Virohan CRM
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : isError ? (
          <div className="bg-rose-50 text-rose-600 p-4 rounded-lg">
            Failed to load analytics: {(error as any)?.message || 'Unknown error'}
          </div>
        ) : (
          /* KPI Cards */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Total Patients</span>
                <Users className="w-5 h-5 text-teal-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {overview?.total_patients || 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Appointments</span>
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {overview?.active_appointments_today || 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Monthly Revenue</span>
                <DollarSign className="w-5 h-5 text-emerald-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                ₹{(overview?.monthly_revenue || 0).toLocaleString('en-IN')}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Pending Leads</span>
                <UserCheck className="w-5 h-5 text-amber-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {overview?.pending_leads || 0}
              </p>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
