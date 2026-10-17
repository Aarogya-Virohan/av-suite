'use client';

import React from 'react';
import Link from 'next/link';
import { AppShell } from '../../../components/layout/AppShell';
import {
  Users,
  Calendar,
  IndianRupee,
  UserCheck,
  Loader2,
  Stethoscope,
  TrendingUp,
  CheckCircle2,
  Receipt,
  AlertCircle,
} from 'lucide-react';
import { useAnalyticsOverview, useMyPerformance } from '../../../features/analytics/api';
import { useAppointments } from '../../../features/appointments/api';
import { useLeads } from '../../../features/leads/api';
import { usePatients } from '../../../features/patients/api';
import { useAuthStore } from '../../../store';
import { canAccessModule, hasCapability } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { formatMoney } from '../../../lib/money';
import {
  Avatar,
  Badge,
  type BadgeTone,
  Card,
  CardHeader,
  KpiCard,
  PageHeader,
} from '../../../components/ui/brand';
import type { Appointment, Lead } from '../../../types/api';

const APPOINTMENT_TONE: Record<string, BadgeTone> = {
  scheduled: 'info',
  completed: 'ok',
  cancelled: 'danger',
  no_show: 'warn',
};

const LEAD_TONE: Record<string, BadgeTone> = {
  new: 'info',
  contacted: 'active',
  qualified: 'warn',
  converted: 'ok',
  lost: 'neutral',
};

function humanise(value: string): string {
  return value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

function greetingFor(hour: number): string {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(
    new Date(iso),
  );
}

function formatDay(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(new Date(iso));
}

/** Upcoming appointments first (soonest at the top), then the most recent past ones. */
function orderAppointments(items: Appointment[]): Appointment[] {
  const now = Date.now();
  const upcoming = items
    .filter((a) => new Date(a.scheduled_at).getTime() >= now)
    .sort((a, b) => +new Date(a.scheduled_at) - +new Date(b.scheduled_at));
  const past = items
    .filter((a) => new Date(a.scheduled_at).getTime() < now)
    .sort((a, b) => +new Date(b.scheduled_at) - +new Date(a.scheduled_at));
  return [...upcoming, ...past];
}

function AppointmentsCard({ items }: { items: Appointment[] }) {
  const rows = orderAppointments(items).slice(0, 7);
  return (
    <Card className="p-5">
      <CardHeader
        title="Appointments"
        action={
          <Link href="/appointments" className="text-[12.5px] font-semibold text-grove hover:underline">
            View all
          </Link>
        }
      />
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted">No appointments yet.</p>
      ) : (
        <table className="w-full border-collapse text-[13.5px]">
          <thead>
            <tr className="border-b border-line text-left text-[11.5px] font-semibold uppercase tracking-wide text-muted">
              <th className="w-[92px] py-2 font-semibold">Time</th>
              <th className="py-2 font-semibold">Patient</th>
              <th className="py-2 font-semibold">Therapist</th>
              <th className="w-[130px] py-2 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((appt) => (
              <tr key={appt.id} className="border-b border-line-soft last:border-b-0">
                <td className="py-2.5 align-middle">
                  <p className="font-semibold tabular-nums text-ink">{formatTime(appt.scheduled_at)}</p>
                  <p className="text-[11.5px] text-slate-400">
                    {formatDay(appt.scheduled_at)} · {appt.duration_minutes} min
                  </p>
                </td>
                <td className="py-2.5 align-middle">
                  <div className="flex items-center gap-2.5">
                    <Avatar name={appt.patient_name} size={32} />
                    <span className="font-semibold text-ink">{appt.patient_name || 'Patient'}</span>
                  </div>
                </td>
                <td className="py-2.5 align-middle">
                  <div className="flex items-center gap-2 text-ink-2">
                    <Avatar name={appt.therapist_name} size={24} />
                    {appt.therapist_name || 'Unassigned'}
                  </div>
                </td>
                <td className="py-2.5 align-middle">
                  <Badge tone={APPOINTMENT_TONE[appt.status] ?? 'neutral'}>{humanise(appt.status)}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function LeadsCard({ items }: { items: Lead[] }) {
  const rows = items.slice(0, 5);
  return (
    <Card className="p-5">
      <CardHeader
        title="Recent leads"
        action={
          <Link href="/leads" className="text-[12.5px] font-semibold text-grove hover:underline">
            View all
          </Link>
        }
      />
      {rows.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">No leads yet.</p>
      ) : (
        <ul>
          {rows.map((lead) => (
            <li key={lead.id} className="flex items-center gap-3 border-b border-line-soft py-2.5 last:border-b-0">
              <Avatar name={lead.name} size={32} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-ink">{lead.name}</p>
                <p className="truncate text-xs text-muted">{lead.source ? humanise(lead.source) : 'Direct'}</p>
              </div>
              <Badge tone={LEAD_TONE[lead.stage] ?? 'neutral'}>{humanise(lead.stage)}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const capabilities = useAuthStore((state) => state.capabilities);
  const clinic = useAuthStore((state) => state.clinic);
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

  // Greeting is computed after mount so the static render and the client agree.
  const [greeting, setGreeting] = React.useState('Welcome back');
  React.useEffect(() => {
    setGreeting(greetingFor(new Date().getHours()));
  }, []);

  if (!canAccessModule('dashboard')) {
    return <AccessRestricted message="Dashboard access is restricted." />;
  }

  const isLoading = canViewFinancials
    ? isOverviewLoading
    : canViewMyPerf
    ? isPerfLoading
    : ((canViewAppts && isApptsLoading) || (canViewLeads && isLeadsLoading) || (canViewPatients && isPatientsLoading));

  const appointments: Appointment[] = (appointmentsRes?.data as Appointment[] | undefined) ?? [];
  const leadItems: Lead[] = (leads as Lead[] | undefined) ?? [];
  const showLists = !isLoading && hasAnyDashboardView && (canViewAppts || canViewLeads);

  return (
    <AppShell>
      <div className="space-y-5">
        <PageHeader
          title={greeting}
          subtitle={`Here is how ${clinic?.name || 'your clinic'} is doing.`}
        />

        {!hasAnyDashboardView ? (
          <Card className="space-y-3 p-8 text-center">
            <h3 className="text-lg font-bold text-ink">No Module Permissions Assigned</h3>
            <p className="mx-auto max-w-md text-sm text-muted">
              Your account currently has no active feature permissions. Please contact your clinic administrator to grant access to patients, appointments, analytics, or other clinic modules.
            </p>
          </Card>
        ) : isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-grove" />
          </div>
        ) : canViewFinancials ? (
          isOverviewError ? (
            <div role="alert" className="flex items-center gap-2 rounded-xl bg-danger-wash p-4 text-danger">
              <AlertCircle className="h-4 w-4" />
              Failed to load analytics: {(overviewError as any)?.message || 'Unknown error'}
            </div>
          ) : (
            /* Admin KPI Cards */
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <KpiCard
                hero
                label="Collected This Month"
                icon={IndianRupee}
                value={formatMoney(overviewData?.revenue.collected_amount_in_period)}
              />
              <KpiCard
                label="Total Patients"
                icon={Users}
                tone="teal"
                value={overviewData?.patients.total_patients ?? 0}
              />
              <KpiCard
                label="Today's Appointments"
                icon={Calendar}
                tone="info"
                value={overviewData?.appointments.today_appointments ?? 0}
              />
              <KpiCard
                label="Billed This Month"
                icon={Receipt}
                tone="grove"
                value={formatMoney(overviewData?.revenue.billed_amount_in_period)}
              />
              <KpiCard
                label="Outstanding (All Time)"
                icon={IndianRupee}
                tone="danger"
                value={formatMoney(overviewData?.revenue.outstanding_amount)}
              />
              <KpiCard
                label="Total Leads"
                icon={UserCheck}
                tone="warn"
                value={overviewData?.leads.total_leads ?? 0}
              />
            </div>
          )
        ) : canViewMyPerf ? (
          /* Personal Clinical KPI Cards */
          isPerfError ? (
            <div role="alert" className="flex items-center gap-2 rounded-xl bg-danger-wash p-4 text-danger">
              <AlertCircle className="h-4 w-4" />
              Failed to load your performance data.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                hero
                label="Today's Visits"
                icon={Calendar}
                value={myPerf?.data?.today_appointments ?? 0}
              />
              <KpiCard
                label="Completed This Month"
                icon={CheckCircle2}
                tone="grove"
                value={myPerf?.data?.completed_appointments_in_period ?? 0}
              />
              <KpiCard
                label="Treatment Sessions"
                icon={Stethoscope}
                tone="teal"
                value={myPerf?.data?.treatment_sessions_in_period ?? 0}
              />
              <KpiCard
                label="Patients Seen"
                icon={Users}
                tone="info"
                value={myPerf?.data?.patients_seen_in_period ?? 0}
              />
            </div>
          )
        ) : (
          /* Front Desk Operational KPI Cards */
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard hero label="Total Patients" icon={Users} value={patientsRes?.meta?.total ?? 0} />
            <KpiCard
              label="Scheduled Appointments"
              icon={Calendar}
              tone="info"
              value={appointmentsRes?.meta?.total ?? appointmentsRes?.data?.length ?? 0}
            />
            <KpiCard label="Active Leads" icon={UserCheck} tone="warn" value={leads?.length ?? 0} />
            <KpiCard
              label="System Status"
              icon={TrendingUp}
              tone="grove"
              value={
                <span className="flex items-center gap-2 text-lg font-bold text-ok">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-fresh" />
                  Operational
                </span>
              }
            />
          </div>
        )}

        {showLists && (
          <div
            className={
              canViewAppts && canViewLeads ? 'grid grid-cols-1 gap-4 xl:grid-cols-[1.85fr_1fr]' : 'grid grid-cols-1 gap-4'
            }
          >
            {canViewAppts && <AppointmentsCard items={appointments} />}
            {canViewLeads && <LeadsCard items={leadItems} />}
          </div>
        )}
      </div>
    </AppShell>
  );
}
