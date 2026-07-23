'use client';

import React, { useState } from 'react';
import { Chart as ChartJS, registerables } from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { useCRMStore } from '@/lib/store';

ChartJS.register(...registerables);

export const AnalyticsView: React.FC = () => {
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month');
  const { patients, invoices, appointments, leads, runningCosts, therapists } = useCRMStore();

  const totalBilled = invoices.reduce((sum, i) => sum + i.total, 0);
  const totalPaid = invoices
    .filter((i) => i.status === 'Paid')
    .reduce((sum, i) => sum + i.total, 0);
  const totalDue = invoices
    .filter((i) => i.status === 'Due' || i.status === 'Partial')
    .reduce((sum, i) => sum + (i.total - i.paidAmount), 0);

  const totalSalaries = therapists.reduce((sum, t) => sum + (t.salary || 0), 0);
  const totalManualExpenses = runningCosts.reduce((sum, c) => sum + (c.amount || 0), 0);
  const totalMonthlyExpenses = totalSalaries + totalManualExpenses;

  const estimatedProfit = totalPaid - totalMonthlyExpenses;

  // Doughnut: Patient Status Breakdown
  const activeCount = patients.filter((p) => p.status === 'Active').length;
  const inactiveCount = patients.filter((p) => p.status === 'Inactive').length;
  const dischargedCount = patients.filter((p) => p.status === 'Discharged').length;

  const patientStatusData = {
    labels: ['Active', 'Inactive', 'Discharged'],
    datasets: [
      {
        data: [activeCount, inactiveCount, dischargedCount],
        backgroundColor: ['#22C55E', '#F59E0B', '#64748B'],
        borderWidth: 0
      }
    ]
  };

  // Doughnut: Lead Sources
  const sourcesMap: Record<string, number> = {};
  leads.forEach((l) => {
    sourcesMap[l.source] = (sourcesMap[l.source] || 0) + 1;
  });

  const leadSourcesData = {
    labels: Object.keys(sourcesMap).length > 0 ? Object.keys(sourcesMap) : ['No Data'],
    datasets: [
      {
        data: Object.keys(sourcesMap).length > 0 ? Object.values(sourcesMap) : [1],
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
          <p className="text-lg font-extrabold text-[var(--teal)] mt-1">₹{totalBilled.toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Collected</p>
          <p className="text-lg font-extrabold text-emerald-600 mt-1">₹{totalPaid.toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Outstanding</p>
          <p className="text-lg font-extrabold text-amber-500 mt-1">₹{totalDue.toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Total Expenses</p>
          <p className="text-lg font-extrabold text-red-500 mt-1">₹{totalMonthlyExpenses.toLocaleString('en-IN')}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Appointments</p>
          <p className="text-lg font-extrabold text-[var(--navy)] dark:text-white mt-1">{appointments.length}</p>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm text-center">
          <p className="text-xs text-[var(--text-light)] font-semibold uppercase">Est. Net Profit</p>
          <p className={`text-lg font-extrabold mt-1 ${estimatedProfit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            ₹{Math.abs(estimatedProfit).toLocaleString('en-IN')} {estimatedProfit < 0 ? '(Loss)' : ''}
          </p>
        </div>
      </div>

      {/* Doughnut Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <h4 className="font-bold text-sm text-[var(--text)]">Patient Status Distribution</h4>
          <div className="h-56 flex items-center justify-center">
            <Doughnut data={patientStatusData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>

        <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-4">
          <h4 className="font-bold text-sm text-[var(--text)]">Lead Acquisition Channels</h4>
          <div className="h-56 flex items-center justify-center">
            <Doughnut data={leadSourcesData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>
      </div>
    </div>
  );
};
