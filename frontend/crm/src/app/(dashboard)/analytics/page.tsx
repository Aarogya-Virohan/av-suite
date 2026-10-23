'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { useAnalyticsOverview, useMyPerformance } from '../../../features/analytics/api';
import { Stethoscope, ClipboardList, TrendingUp, Users, Calendar, IndianRupee, Wallet, ArrowDownRight, Info } from 'lucide-react';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { formatMoney } from '../../../lib/money';
import { useAuthStore } from '../../../store';
import type { AnalyticsPeriod, PatientRevenueSort } from '../../../types/api';
import { canAccessModule, hasCapability } from '../../../config/permissions';
import { Avatar, Card, CardHeader, KpiCard, PageHeader, type IconTone } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

export default function AnalyticsPage() {
  const capabilities = useAuthStore((state) => state.capabilities);
  const [period, setPeriod] = useState<AnalyticsPeriod>('month');
  const [patientRevenueSort, setPatientRevenueSort] = useState<PatientRevenueSort>('collected_amount');

  const clinicFinancialsKeyPresent = Object.prototype.hasOwnProperty.call(capabilities, 'analytics.clinic_financials');
  const myPerformanceKeyPresent = Object.prototype.hasOwnProperty.call(capabilities, 'analytics.my_performance');
  const canViewFinancials =
    clinicFinancialsKeyPresent && hasCapability('analytics.clinic_financials');
  const canViewMyPerf =
    myPerformanceKeyPresent && hasCapability('analytics.my_performance');

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
    const perfCards: { label: string; value: number; icon: React.ElementType; tone: IconTone }[] = [
      { label: "Today's Appointments", value: perf?.today_appointments ?? 0, icon: Calendar, tone: 'grove' },
      { label: `Completed (${selectedPeriodLabel})`, value: perf?.completed_appointments_in_period ?? 0, icon: TrendingUp, tone: 'grove' },
      { label: `Cancelled (${selectedPeriodLabel})`, value: perf?.cancelled_appointments_in_period ?? 0, icon: ArrowDownRight, tone: 'danger' },
      { label: `Treatment Sessions (${selectedPeriodLabel})`, value: perf?.treatment_sessions_in_period ?? 0, icon: Stethoscope, tone: 'teal' },
      { label: `SOAP Notes (${selectedPeriodLabel})`, value: perf?.soap_notes_in_period ?? 0, icon: ClipboardList, tone: 'info' },
      { label: `Patients Seen (${selectedPeriodLabel})`, value: perf?.patients_seen_in_period ?? 0, icon: Users, tone: 'warn' },
    ];
    return (
      <AppShell>
        <div className="space-y-6">
          <PageHeader
            title="My Performance"
            subtitle="Your own activity for the selected reporting period"
            actions={<PeriodSelector period={period} onChange={setPeriod} />}
          />
          {performanceEnvelope?.meta.period === period && (
            <RangeNote start={performanceEnvelope.meta.start} end={performanceEnvelope.meta.end} />
          )}

          {myPerfLoading ? (
            <Card className="p-6 text-sm text-muted">Loading your performance data...</Card>
          ) : myPerfError ? (
            <Card role="alert" className="border-danger/30 bg-danger-wash p-4 text-sm font-medium text-danger">
              Unable to load your performance data.
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {perfCards.map(({ label, value, icon, tone }, index) => (
                <KpiCard key={label} label={label} value={value} icon={icon} tone={tone} hero={index === 0} />
              ))}
            </div>
          )}
        </div>
      </AppShell>
    );
  }

  const patientRevenue = analyticsOverview?.patient_revenue ?? [];
  const maxRanked = Math.max(
    0,
    ...patientRevenue.map((p) => Number(patientRevenueSort === 'billed_amount' ? p.billed_amount : p.collected_amount) || 0),
  );

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Analytics & Financial Summary"
          subtitle="Clinic financial activity for the selected reporting period"
          actions={<PeriodSelector period={period} onChange={setPeriod} />}
        />
        {overviewEnvelope?.meta.period === period && (
          <RangeNote start={overviewEnvelope.meta.start} end={overviewEnvelope.meta.end} />
        )}

        {overviewLoading ? (
          <Card role="status" className="p-6 text-sm text-muted">Loading analytics for {period}...</Card>
        ) : overviewError ? (
          <Card role="alert" className="border-danger/30 bg-danger-wash p-4 text-sm font-medium text-danger">
            Unable to load clinic analytics.
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <KpiCard
                hero
                label={`Collected (${selectedPeriodLabel})`}
                value={formatMoney(analyticsOverview?.revenue.collected_amount_in_period)}
                icon={Wallet}
              />
              <KpiCard
                label={`Billed (${selectedPeriodLabel})`}
                value={formatMoney(analyticsOverview?.revenue.billed_amount_in_period)}
                icon={IndianRupee}
                tone="grove"
              />
              <KpiCard
                label="Outstanding balance (all time)"
                value={formatMoney(analyticsOverview?.revenue.outstanding_amount)}
                icon={ArrowDownRight}
                tone="warn"
              />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
              <Card className="p-6">
                <CardHeader
                  title="Top Patients by Revenue"
                  action={
                    <label className="flex items-center gap-2 text-xs font-medium text-muted">
                      Rank by
                      <select
                        aria-label="Rank patients by"
                        value={patientRevenueSort}
                        onChange={(event) => setPatientRevenueSort(event.target.value as PatientRevenueSort)}
                        className="h-8 cursor-pointer rounded-lg border border-line bg-card px-2 text-xs font-semibold text-ink-2 focus:border-grove focus:outline-none dark:border-slate-700 dark:bg-slate-950"
                      >
                        <option value="collected_amount">Collected</option>
                        <option value="billed_amount">Billed</option>
                      </select>
                    </label>
                  }
                />
                {!patientRevenue.length ? (
                  <p className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">
                    No patient financial activity for this period.
                  </p>
                ) : (
                  <div className="divide-y divide-line-soft">
                    {patientRevenue.map((patient, index) => {
                      const ranked =
                        Number(patientRevenueSort === 'billed_amount' ? patient.billed_amount : patient.collected_amount) || 0;
                      const width = maxRanked > 0 && ranked > 0 ? Math.max(4, Math.round((ranked / maxRanked) * 100)) : 0;
                      return (
                        <div
                          key={patient.patient_id}
                          className="grid grid-cols-[20px_minmax(0,1fr)_104px_104px] items-center gap-4 py-3 text-sm"
                        >
                          <span className="text-xs font-bold tabular-nums text-slate-400">{index + 1}</span>
                          <div className="flex min-w-0 items-center gap-3">
                            <Avatar name={patient.patient_name} size={32} />
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-semibold text-ink">{patient.patient_name}</p>
                              <div className="mt-1.5 h-1.5 rounded-full bg-line-soft" aria-hidden="true">
                                <div className="h-full rounded-full bg-gradient-to-r from-grove to-fresh" style={{ width: `${width}%` }} />
                              </div>
                            </div>
                          </div>
                          <p className="text-right tabular-nums text-ink-2">
                            <span className="block text-[10.5px] font-medium text-muted">Billed</span>
                            {formatMoney(patient.billed_amount)}
                          </p>
                          <p className="text-right font-semibold tabular-nums text-ink">
                            <span className="block text-[10.5px] font-medium text-muted">Collected</span>
                            {formatMoney(patient.collected_amount)}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card className="h-fit space-y-2 p-6">
                <div className="flex items-center gap-2.5">
                  <span className="grid h-8 w-8 place-items-center rounded-[9px] bg-info-wash text-info">
                    <Info className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <h2 className="font-display text-[15.5px] font-bold text-ink">Running costs & net profit unavailable</h2>
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  Clinic expenses and salaries are not recorded in AV Suite yet, so profit cannot be calculated. Figures here are revenue only.
                </p>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

const rangeDate = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

/** The API returns [start, end) as UTC timestamps; show the last included day, not the exclusive end. */
function rangeLabel(start: string, end: string) {
  const s = new Date(start.slice(0, 10) + 'T00:00:00Z');
  const e = new Date(new Date(end.slice(0, 10) + 'T00:00:00Z').getTime() - 86_400_000);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return '';
  const a = rangeDate.format(s);
  const b = rangeDate.format(e < s ? s : e);
  return a === b ? a : `${a} to ${b}`;
}

function RangeNote({ start, end }: { start: string; end: string }) {
  return (
    <p className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-3 py-1 text-xs text-muted">
      Showing {rangeLabel(start, end)}
    </p>
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
      className="flex items-center gap-1 rounded-xl border border-line bg-card p-1 shadow-card dark:border-slate-800 dark:bg-slate-900"
    >
      {(['today', 'week', 'month', 'year'] as const).map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={period === value}
          onClick={() => onChange(value)}
          className={cn(
            'cursor-pointer rounded-lg px-3.5 py-1.5 text-xs font-semibold capitalize transition-colors',
            period === value ? 'bg-midnight text-white shadow-sm' : 'text-muted hover:bg-canvas hover:text-ink',
          )}
        >
          {value}
        </button>
      ))}
    </div>
  );
}
