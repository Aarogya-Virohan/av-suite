'use client';

import React from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { Users, Calendar, DollarSign, UserCheck, Loader2, Stethoscope, TrendingUp, CheckCircle2 } from 'lucide-react';
import { useAnalyticsOverview, useMyPerformance } from '../../../features/analytics/api';
import { useAppointments } from '../../../features/appointments/api';
import { useLeads } from '../../../features/leads/api';
import { usePatients } from '../../../features/patients/api';
import { useAuthStore } from '../../../store';
import { canAccessModule, hasCapability } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { formatMoney } from '../../../lib/money';

export default function DashboardPage() {
  const capabilities = useAuthStore((state) => state.capabilities);
  const canViewFinancials =
    Object.prototype.hasOwnProperty.call(capabilities, 'analytics.clinic_financials') &&
    hasCapability('analytics.clinic_financials');
  const canViewMyPerf =
    Object.prototype.hasOwnProperty.call(capabilities, 'analytics.my_performance') &&
    hasCapability('analytics.my_performance');
  const canViewAppts =
    Object.prototype.hasOwnProperty.call(capabilities, 'appointments.view') &&
    hasCapability('appointments.view');
  const canViewLeads =
    Object.prototype.hasOwnProperty.call(capabilities, 'leads.view') &&
    hasCapability('leads.view');
  const canViewPatients =
    Object.prototype.hasOwnProperty.call(capabilities, 'patients.view') &&
    hasCapability('patients.view');

  const hasAnyDashboardView = canViewFinancials || canViewMyPerf || canViewAppts || canViewLeads || canViewPatients;

  // Admin / financial overview query
  const { data: overview, isLoading: isOverviewLoading, isError: isOverviewError, error: overviewError } =
    useAnalyticsOverview({ enabled: canViewFinancials });
  const overviewData = overview?.data;
  
  // Therapist personal clinical performance query
  const { data: myPerf, isLoading: isPerfLoading, isError: isPerfError } =
    useMyPerformance('month', canViewMyPerf && !canViewFinancials);

  // Operational queries
  const { data: appointmentsRes, isLoading: isApptsLoading } = useAppointments(undefined, undefined, 1, 50, canViewAppts);
  const { data: leads, isLoading: isLeadsLoading } = useLeads(undefined, canViewLeads);
  const { data: patientsRes, isLoading: isPatientsLoading } = usePatients(undefined, 1, 1, canViewPatients);

  if (!canAccessModule('dashboard')) {
    return <AccessRestricted message="Dashboard access is restricted." />;
  }

  const isLoading = canViewFinancials 
    ? isOverviewLoading 
    : canViewMyPerf 
    ? isPerfLoading 
    : ((canViewAppts && isApptsLoading) || (canViewLeads && isLeadsLoading) || (canViewPatients && isPatientsLoading));

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Welcome back to Aarogya Virohan CRM
          </p>
        </div>

        {!hasAnyDashboardView ? (
          <div className="p-8 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-center space-y-3">
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">No Module Permissions Assigned</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Your account currently has no active feature permissions. Please contact your clinic administrator to grant access to patients, appointments, analytics, or other clinic modules.
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : canViewFinancials ? (

          isOverviewError ? (
            <div className="bg-rose-50 text-rose-600 p-4 rounded-lg">
              Failed to load analytics: {(overviewError as any)?.message || 'Unknown error'}
            </div>
          ) : (
            /* Admin KPI Cards */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Total Patients</span>
                  <Users className="w-5 h-5 text-teal-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overviewData?.patients.total_patients ?? 0}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Appointments</span>
                  <Calendar className="w-5 h-5 text-blue-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overviewData?.appointments.today_appointments ?? 0}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Billed This Month</span>
                  <DollarSign className="w-5 h-5 text-emerald-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {formatMoney(overviewData?.revenue.billed_amount_in_period)}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Collected This Month</span>
                  <DollarSign className="w-5 h-5 text-teal-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {formatMoney(overviewData?.revenue.collected_amount_in_period)}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Outstanding (All Time)</span>
                  <DollarSign className="w-5 h-5 text-rose-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {formatMoney(overviewData?.revenue.outstanding_amount)}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-slate-400">Total Leads</span>
                  <UserCheck className="w-5 h-5 text-amber-600" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                  {overviewData?.leads.total_leads ?? 0}
                </p>
              </div>
            </div>
          )
        ) : canViewMyPerf ? (
          /* Personal Clinical KPI Cards */
          isPerfError ? (
            <div role="alert" className="bg-rose-50 text-rose-600 p-4 rounded-lg">
              Failed to load your performance data.
            </div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Visits</span>
                <Calendar className="w-5 h-5 text-teal-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.data?.today_appointments ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Completed This Month</span>
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.data?.completed_appointments_in_period ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Treatment Sessions</span>
                <Stethoscope className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.data?.treatment_sessions_in_period ?? 0}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-400">Patients Seen</span>
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
                {myPerf?.data?.patients_seen_in_period ?? 0}
              </p>
            </div>
          </div>
          )
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
