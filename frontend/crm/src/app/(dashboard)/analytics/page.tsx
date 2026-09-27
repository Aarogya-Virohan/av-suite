'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { useAnalyticsOverview, useMyPerformance } from '../../../features/analytics/api';
import { ActivitySquare, Stethoscope, ClipboardList, TrendingUp, Users, Calendar, DollarSign, ArrowDownRight } from 'lucide-react';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { formatMoney } from '../../../lib/money';
import type { AnalyticsPeriod, PatientRevenueSort } from '../../../types/api';
import { canAccessModule, hasCapability } from '../../../config/permissions';

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('month');
  const [patientRevenueSort, setPatientRevenueSort] = useState<PatientRevenueSort>('collected_amount');

  const canViewFinancials = hasCapability('analytics.clinic_financials');
  const canViewMyPerf = hasCapability('analytics.my_performance');

  const { data: performanceEnvelope, isLoading: myPerfLoading, isError: myPerfError } =
    useMyPerformance(period, canViewMyPerf && !canViewFinancials);
  const myPerformance = performanceEnvelope?.data;
  const { data: overviewEnvelope, isLoading: overviewLoading, isError: overviewError } =
    useAnalyticsOverview({ period, enabled: canViewFinancials, patientRevenueSort });
  const analyticsOverview = overviewEnvelope?.data;
  const selectedPeriodLabel = period[0].toUpperCase() + period.slice(1);

  if (!canAccessModule('analytics')) {
    return <AccessRestricted message="Analytics access is restricted for your role." />;
  }

  // If user only has personal performance permission, show personal performance
  if (!canViewFinancials && canViewMyPerf) {
    const perf = myPerformance;
    return (
      <AppShell>
        <div className="p-6 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-indigo-100 dark:bg-indigo-900/40">
              <ActivitySquare className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">My Performance</h1>
              <p className="text-xs text-slate-400">Your own activity for the selected reporting period</p>
            </div>
            <PeriodSelector period={period} onChange={setPeriod} />
          </div>
          {performanceEnvelope?.meta.period === period && (
            <p className="text-xs text-slate-400">
              UTC range: {performanceEnvelope.meta.start.slice(0, 10)} – {performanceEnvelope.meta.end.slice(0, 10)} (end exclusive)
            </p>
          )}

          {myPerfLoading ? (
            <div className="text-slate-400 text-sm">Loading your performance data...</div>
          ) : myPerfError ? (
            <div role="alert" className="text-rose-600 text-sm">Unable to load your performance data.</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { label: "Today's Appointments", value: perf?.today_appointments ?? 0, icon: Calendar },
                { label: `Completed (${selectedPeriodLabel})`, value: perf?.completed_appointments_in_period ?? 0, icon: TrendingUp },
                { label: `Cancelled (${selectedPeriodLabel})`, value: perf?.cancelled_appointments_in_period ?? 0, icon: ArrowDownRight },
                { label: `Treatment Sessions (${selectedPeriodLabel})`, value: perf?.treatment_sessions_in_period ?? 0, icon: Stethoscope },
                { label: `SOAP Notes (${selectedPeriodLabel})`, value: perf?.soap_notes_in_period ?? 0, icon: ClipboardList },
                { label: `Patients Seen (${selectedPeriodLabel})`, value: perf?.patients_seen_in_period ?? 0, icon: Users },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-100 dark:border-slate-700">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="w-4 h-4 text-indigo-500" />
                    <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
                  </div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header & Period Tabs */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analytics & Financial Summary</h1>
            <p className="text-sm text-slate-500">Clinic financial activity for the selected reporting period</p>
          </div>

          <PeriodSelector period={period} onChange={setPeriod} />
        </div>
        {overviewEnvelope?.meta.period === period && (
          <p className="text-xs text-slate-400">
            UTC range: {overviewEnvelope.meta.start.slice(0, 10)} – {overviewEnvelope.meta.end.slice(0, 10)} (end exclusive)
          </p>
        )}

        {overviewLoading ? (
          <div role="status" className="text-sm text-slate-500">Loading analytics for {period}...</div>
        ) : overviewError ? (
          <div role="alert" className="text-sm text-rose-600">Unable to load clinic analytics.</div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricCard label={`Billed (${selectedPeriodLabel})`} value={formatMoney(analyticsOverview?.revenue.billed_amount_in_period)} icon={DollarSign} />
              <MetricCard label={`Collected (${selectedPeriodLabel})`} value={formatMoney(analyticsOverview?.revenue.collected_amount_in_period)} icon={DollarSign} />
              <MetricCard label="Outstanding balance (all time)" value={formatMoney(analyticsOverview?.revenue.outstanding_amount)} icon={ArrowDownRight} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-3">
                <h2 className="text-base font-bold text-slate-900 dark:text-white">Running costs & net profit unavailable</h2>
                <p className="text-sm text-slate-500">Expense and salary data is not persisted by the backend, so no expense or profit estimate is shown.</p>
              </section>

              <section className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">Top Patients by Revenue</h2>
                  <label className="flex items-center gap-2 text-xs text-slate-500">
                    Rank by
                    <select
                      aria-label="Rank patients by"
                      value={patientRevenueSort}
                      onChange={(event) => setPatientRevenueSort(event.target.value as PatientRevenueSort)}
                      className="rounded-lg border border-slate-200 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-950"
                    >
                      <option value="collected_amount">Collected</option>
                      <option value="billed_amount">Billed</option>
                    </select>
                  </label>
                </div>
                {overviewLoading ? (
                  <p role="status" className="text-sm text-slate-500">Loading patient revenue...</p>
                ) : overviewError ? (
                  <p role="alert" className="text-sm text-rose-600">Unable to load patient revenue.</p>
                ) : !analyticsOverview?.patient_revenue.length ? (
                  <p className="text-sm text-slate-500">No patient financial activity for this period.</p>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {analyticsOverview.patient_revenue.map((patient) => (
                      <div key={patient.patient_id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4 py-3 text-xs">
                        <p className="font-bold text-slate-900 dark:text-white">{patient.patient_name}</p>
                        <p className="text-right"><span className="block text-[10px] text-slate-400">Billed</span>{formatMoney(patient.billed_amount)}</p>
                        <p className="text-right"><span className="block text-[10px] text-slate-400">Collected</span>{formatMoney(patient.collected_amount)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function PeriodSelector({
  period,
  onChange,
}: {
  period: AnalyticsPeriod;
  onChange: (period: AnalyticsPeriod) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Reporting period"
      className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800"
    >
      {(['today', 'week', 'month', 'year'] as const).map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={period === value}
          onClick={() => onChange(value)}
          className={`px-3 py-1.5 text-xs font-bold uppercase rounded-lg transition-all cursor-pointer ${
            period === value
              ? 'bg-teal-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
          }`}
        >
          {value}
        </button>
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase text-slate-400">{label}</span>
        <Icon className="w-5 h-5 text-teal-600" />
      </div>
      <p className="text-2xl font-extrabold text-slate-900 dark:text-white mt-2">{value}</p>
    </div>
  );
}
