'use client';

import React from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { Users, Calendar, DollarSign, UserCheck } from 'lucide-react';
import { mockAnalyticsOverview } from '../../../mocks';

export default function DashboardPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Welcome back to Aarogya Virohan CRM
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-slate-400">Total Patients</span>
              <Users className="w-5 h-5 text-teal-600" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
              {mockAnalyticsOverview.total_patients}
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-slate-400">Today&apos;s Appointments</span>
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
              {mockAnalyticsOverview.active_appointments_today}
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-slate-400">Monthly Revenue</span>
              <DollarSign className="w-5 h-5 text-emerald-600" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
              ₹{mockAnalyticsOverview.monthly_revenue.toLocaleString('en-IN')}
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-slate-400">Pending Leads</span>
              <UserCheck className="w-5 h-5 text-amber-600" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">
              {mockAnalyticsOverview.pending_leads}
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
