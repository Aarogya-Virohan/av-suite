'use client';

import React from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { Users, Calendar, DollarSign, UserCheck, Loader2, Stethoscope, TrendingUp, CheckCircle2 } from 'lucide-react';
import { useAnalyticsOverview, useMyPerformance } from '../../../features/analytics/api';
import { useAppointments } from '../../../features/appointments/api';
import { useLeads } from '../../../features/leads/api';
import { usePatients } from '../../../features/patients/api';
import { useAuthStore } from '../../../store';
import { canAccessModule } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';

export default function DashboardPage() {
  const role = useAuthStore((s) => s.role);
  
  // Admin queries full clinic overview
  const { data: overview, isLoading: isOverviewLoading, isError: isOverviewError, error: overviewError } = useAnalyticsOverview(role === 'admin');
  
  // Therapist queries personal clinical performance
  const { data: myPerf, isLoading: isPerfLoading, isError: isPerfError } = useMyPerformance(role === 'therapist');

  // Front desk queries appointments & leads
  const { data: appointmentsRes, isLoading: isApptsLoading } = useAppointments(undefined, undefined, 1, 50);
  const { data: leads, isLoading: isLeadsLoading } = useLeads();
  const { data: patientsRes, isLoading: isPatientsLoading } = usePatients(undefined, 1, 1);

  if (!canAccessModule(role, 'dashboard')) {
    return <AccessRestricted message="Dashboard access is restricted." />;
  }

  const isLoading = role === 'admin' 
    ? isOverviewLoading 
    : role === 'therapist' 
    ? isPerfLoading 
    : (isApptsLoading || isLeadsLoading || isPatientsLoading);

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
        ) : role === 'admin' ? (
          isOverviewError ? (
            <div className="bg-rose-50 text-rose-600 p-4 rounded-lg">
              Failed to load analytics: {(overviewError as any)?.message || 'Unknown error'}
            </div>
          ) : (
            /* Admin KPI Cards */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Total Patients</span>
                  <Users className="w-5 h-5 text-teal-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overview?.patients?.total_patients || 0}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Appointments</span>
                  <Calendar className="w-5 h-5 text-blue-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overview?.appointments?.today_appointments || 0}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Monthly Revenue</span>
                  <DollarSign className="w-5 h-5 text-emerald-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  ₹{(overview?.revenue?.revenue_this_month || 0).toLocaleString('en-IN')}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Pending Leads</span>
                  <UserCheck className="w-5 h-5 text-amber-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overview?.leads?.total_leads || 0}
                </p>
              </div>
            </div>
          )
        ) : role === 'therapist' ? (
          /* Therapist Clinical KPI Cards */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Visits</span>
                <Calendar className="w-5 h-5 text-teal-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.today_appointments ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Completed This Month</span>
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.completed_appointments_this_month ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Treatment Sessions</span>
                <Stethoscope className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.treatment_sessions_this_month ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Patients Seen</span>
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.patients_seen_this_month ?? 0}
              </p>
            </div>
          </div>
        ) : (
          /* Front Desk Operational KPI Cards */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Total Patients</span>
                <Users className="w-5 h-5 text-teal-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {patientsRes?.meta?.total ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Scheduled Appointments</span>
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {appointmentsRes?.meta?.total ?? appointmentsRes?.data?.length ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Active Leads</span>
                <UserCheck className="w-5 h-5 text-amber-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {leads?.length ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">System Status</span>
                <TrendingUp className="w-5 h-5 text-emerald-600" />
              </div>
              <p className="text-lg font-bold text-emerald-600 mt-2 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                Operational
              </p>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
