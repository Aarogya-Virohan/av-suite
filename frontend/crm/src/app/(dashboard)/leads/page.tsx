'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { useLeads, useUpdateLeadStage, useConvertLead } from '../../../features/leads/api';
import { AddLeadSlideOver } from '../../../features/leads/components/AddLeadSlideOver';
import { LostReasonSlideOver } from '../../../features/leads/components/LostReasonSlideOver';
import { lostReasonLabel } from '../../../features/leads/lostReasons';
import { Lead, LeadStage } from '../../../types/api';
import { Plus, UserCheck, Phone, Mail, Search, List, LayoutGrid, CalendarClock, Loader2, Download, BarChart3 } from 'lucide-react';
import { downloadCsv, leadsToCsv, monthlyLeadCounts } from '../../../features/leads/report';
import { localToday } from '../../../lib/datetime';
import { toast } from 'sonner';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import {
  Avatar,
  Badge,
  type BadgeTone,
  Button,
  Card,
  PageHeader,
  SegmentGroup,
  SegmentTab,
} from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

const STAGES: { key: LeadStage; label: string; tone: BadgeTone; dot: string }[] = [
  { key: 'new', label: 'New', tone: 'info', dot: 'bg-info' },
  { key: 'contacted', label: 'Contacted', tone: 'warn', dot: 'bg-warn' },
  { key: 'qualified', label: 'Qualified', tone: 'active', dot: 'bg-logo-teal' },
  { key: 'converted', label: 'Converted', tone: 'ok', dot: 'bg-fresh' },
  { key: 'lost', label: 'Lost', tone: 'neutral', dot: 'bg-slate-400' },
];

const STAGE_SELECT: Record<LeadStage, string> = {
  new: 'border-info/25 bg-info-wash text-info',
  contacted: 'border-warn/25 bg-warn-wash text-warn',
  qualified: 'border-logo-teal/30 bg-logo-teal-wash text-logo-teal-ink',
  converted: 'border-ok/25 bg-ok-wash text-ok',
  lost: 'border-line bg-slate-100 text-slate-600',
};

const createdDateFormat = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

function formatCreated(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : createdDateFormat.format(date);
}

const sourceLabel = (source: string | null | undefined) => (source ? source.replace(/_/g, ' ') : null);

const isConverted = (lead: Lead) => lead.stage === 'converted' || !!lead.converted_patient_id;
// A lost lead cannot be converted; move it back to an open stage first (founder feedback, X-1).
const isLost = (lead: Lead) => lead.stage === 'lost';

export default function LeadsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const hasAccess = canAccessModule('leads');
  const canCreateLead = hasCapability('leads.create');
  const canConvertLead = hasCapability('leads.convert');
  const canEditLead = hasCapability('leads.edit');

  const { data: leads = [], isLoading } = useLeads(undefined, hasAccess);
  const updateStage = useUpdateLeadStage();
  const convertLead = useConvertLead();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('list');
  const [searchQuery, setSearchQuery] = useState('');
  const [showMonthly, setShowMonthly] = useState(false);
  // Lead waiting for a lost reason before its stage changes (D-026).
  const [lostLead, setLostLead] = useState<Lead | null>(null);

  const handleConvert = async (leadId: string, leadName: string) => {
    try {
      await convertLead.mutateAsync(leadId);
      toast.success(`Lead ${leadName} converted to Patient successfully!`);
    } catch (err) {
      console.error(err);
      toast.error('Failed to convert lead');
    }
  };

  const handleStageChange = async (leadId: string, newStage: LeadStage) => {
    if (newStage === 'lost') {
      const lead = leads.find((l) => l.id === leadId);
      if (lead) setLostLead(lead);
      return;
    }
    try {
      await updateStage.mutateAsync({ id: leadId, stage: newStage });
      toast.success('Lead stage updated');
    } catch (err) {
      console.error(err);
      toast.error('Failed to update lead stage');
    }
  };

  const handleLostSave = async (reason: string, remark: string) => {
    if (!lostLead) return;
    try {
      await updateStage.mutateAsync({
        id: lostLead.id,
        stage: 'lost',
        lost_reason: reason,
        lost_remark: remark ? remark : null,
      });
      toast.success(lostLead.stage === 'lost' ? 'Lost reason updated' : 'Lead marked as lost');
      setLostLead(null);
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to save the lost reason');
    }
  };

  const lostReasonNote = (lead: Lead) =>
    isLost(lead) && lead.lost_reason ? (
      <button
        type="button"
        onClick={() => canEditLead && setLostLead(lead)}
        disabled={!canEditLead}
        title={lead.lost_remark || (canEditLead ? 'Edit lost reason' : undefined)}
        className="mt-1 block max-w-[220px] truncate text-left text-[11.5px] text-muted enabled:cursor-pointer enabled:hover:text-ink enabled:hover:underline"
      >
        {lostReasonLabel(lead.lost_reason)}
        {lead.lost_remark ? `: ${lead.lost_remark}` : ''}
      </button>
    ) : isLost(lead) && canEditLead ? (
      <button
        type="button"
        onClick={() => setLostLead(lead)}
        className="mt-1 block cursor-pointer text-[11.5px] font-semibold text-grove hover:underline"
      >
        Add reason
      </button>
    ) : null;

  if (!hasAccess) {
    // AccessRestricted renders its own AppShell.
    return <AccessRestricted message="You do not have permission to view or manage leads." />;
  }

  const filteredLeads = leads.filter((lead) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      lead.name.toLowerCase().includes(q) ||
      lead.phone.includes(q) ||
      (lead.email && lead.email.toLowerCase().includes(q))
    );
  });

  const stageCounts = STAGES.map((stage) => ({
    ...stage,
    count: leads.filter((l) => l.stage === stage.key).length,
  }));

  const stageSelect = (lead: Lead, compact = false) => (
    <select
      aria-label={`Stage for ${lead.name}`}
      value={lead.stage}
      onChange={(e) => handleStageChange(lead.id, e.target.value as LeadStage)}
      disabled={!canEditLead || isConverted(lead)}
      className={cn(
        'cursor-pointer rounded-lg border font-semibold focus:outline-none focus:ring-2 focus:ring-grove/20 disabled:cursor-not-allowed disabled:opacity-60',
        compact ? 'h-8 flex-1 px-2 text-[11.5px]' : 'h-9 px-3 text-xs',
        STAGE_SELECT[lead.stage] ?? STAGE_SELECT.lost,
      )}
    >
      {STAGES.map((s) => (
        <option key={s.key} value={s.key}>
          {s.label}
        </option>
      ))}
    </select>
  );

  const convertButton = (lead: Lead, compact = false) => (
    <button
      onClick={() => handleConvert(lead.id, lead.name)}
      className={cn(
        'inline-flex cursor-pointer items-center gap-1.5 rounded-lg bg-ok-wash font-semibold text-ok transition-colors hover:bg-[#d3eedc]',
        compact ? 'h-8 px-2.5 text-[11.5px]' : 'h-9 px-3 text-xs',
      )}
    >
      <UserCheck className="h-3.5 w-3.5" />
      <span>Convert</span>
    </button>
  );

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Patient Leads"
          subtitle="Track and convert prospective patients"
          actions={
            <>
              {leads.length > 0 && (
                <>
                  <Button variant="secondary" onClick={() => setShowMonthly((v) => !v)} aria-pressed={showMonthly}>
                    <BarChart3 className="h-4 w-4" />
                    <span className="hidden sm:inline">Monthly</span>
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => downloadCsv(`leads-${localToday()}.csv`, leadsToCsv(filteredLeads))}
                    title="Download the leads shown below as a CSV file (opens in Excel)"
                  >
                    <Download className="h-4 w-4" />
                    <span className="hidden sm:inline">Export CSV</span>
                  </Button>
                </>
              )}
              <SegmentGroup>
                <SegmentTab active={viewMode === 'list'} onClick={() => setViewMode('list')} icon={List}>
                  <span className="hidden sm:inline">List</span>
                </SegmentTab>
                <SegmentTab active={viewMode === 'kanban'} onClick={() => setViewMode('kanban')} icon={LayoutGrid}>
                  <span className="hidden sm:inline">Kanban</span>
                </SegmentTab>
              </SegmentGroup>
              {canCreateLead && (
                <Button onClick={() => setIsAddOpen(true)}>
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline">Add Lead</span>
                </Button>
              )}
            </>
          }
        />

        {/* Stage summary + search */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, phone, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-10 w-full rounded-[10px] border border-line bg-card pl-9 pr-4 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 dark:border-slate-800 dark:bg-slate-900 dark:text-white"
            />
          </div>
          {!isLoading && leads.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {stageCounts.map((stage) => (
                <span
                  key={stage.key}
                  className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-2.5 py-1 text-xs font-medium text-ink-2"
                >
                  <span className={cn('h-2 w-2 rounded-full', stage.dot)} aria-hidden="true" />
                  {stage.label}
                  <span className="font-bold tabular-nums text-ink">{stage.count}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {showMonthly && !isLoading && (
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-3">
              <h2 className="font-display text-[15px] font-bold text-ink">Leads by month</h2>
              <span className="text-xs text-muted">Last 6 months, by date added</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] font-bold uppercase tracking-wider text-muted">
                    <th className="px-5 py-2.5">Month</th>
                    <th className="px-5 py-2.5 text-right">New leads</th>
                    <th className="px-5 py-2.5 text-right">Converted</th>
                    <th className="px-5 py-2.5 text-right">Lost</th>
                    <th className="px-5 py-2.5 text-right">Still open</th>
                    <th className="px-5 py-2.5 text-right">Conversion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {monthlyLeadCounts(leads).map((m) => (
                    <tr key={m.key}>
                      <td className="px-5 py-2.5 font-semibold text-ink">{m.label}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums">{m.total}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums text-ok">{m.converted}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums text-danger">{m.lost}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums">{m.open}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums text-muted">
                        {m.total ? `${Math.round((m.converted / m.total) * 100)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {isLoading ? (
          <Card className="flex h-64 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-grove" aria-label="Loading leads" />
          </Card>
        ) : viewMode === 'list' ? (
          /* List View (Default) */
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-line bg-canvas/60 dark:border-slate-800 dark:bg-slate-950">
                    {['Lead', 'Contact', 'Source', 'Stage'].map((h) => (
                      <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                        {h}
                      </th>
                    ))}
                    <th className="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft dark:divide-slate-800">
                  {filteredLeads.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-12 text-center text-sm text-muted">
                        No leads found matching your search.
                      </td>
                    </tr>
                  ) : (
                    filteredLeads.map((lead) => (
                      <tr key={lead.id}>
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <Avatar name={lead.name} size={36} />
                            <div>
                              <p className="text-sm font-semibold text-ink">{lead.name}</p>
                              <div className="mt-0.5 flex items-center gap-1 text-xs text-muted">
                                <CalendarClock className="h-3 w-3" />
                                <span>{formatCreated(lead.created_at)}</span>
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="space-y-1 text-sm text-ink-2">
                            <div className="flex items-center gap-2">
                              <Phone className="h-3.5 w-3.5 text-slate-400" />
                              <span className="tabular-nums">{lead.phone}</span>
                            </div>
                            {lead.email && (
                              <div className="flex items-center gap-2">
                                <Mail className="h-3.5 w-3.5 text-slate-400" />
                                <span>{lead.email}</span>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <Badge tone="neutral" className="capitalize">
                            {sourceLabel(lead.source) || 'Unknown'}
                          </Badge>
                        </td>
                        <td className="px-5 py-3.5">
                          {stageSelect(lead)}
                          {lostReasonNote(lead)}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          {isLost(lead) ? (
                            <span className="text-xs text-muted">Lost</span>
                          ) : !isConverted(lead) ? (
                            canConvertLead ? (
                              convertButton(lead)
                            ) : (
                              <span className="text-xs italic text-slate-400">No convert permission</span>
                            )
                          ) : (
                            <Badge tone="ok">Converted</Badge>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        ) : (
          /* Kanban View */
          <div className="flex w-full snap-x items-start gap-4 overflow-x-auto pb-4">
            {STAGES.map((stage) => {
              const stageLeads = filteredLeads.filter((l) => l.stage === stage.key);
              return (
                <div
                  key={stage.key}
                  className="flex min-h-[500px] min-w-[280px] flex-shrink-0 snap-start flex-col space-y-3 rounded-2xl border border-line bg-canvas p-3 sm:min-w-[300px] dark:border-slate-800 dark:bg-slate-900/50"
                >
                  <div className="flex items-center justify-between px-1 pb-1">
                    <div className="flex items-center gap-2.5">
                      <span className={cn('h-2.5 w-2.5 rounded-full', stage.dot)} aria-hidden="true" />
                      <span className="font-display text-sm font-bold text-ink">{stage.label}</span>
                    </div>
                    <span className="rounded-full border border-line bg-card px-2.5 py-0.5 text-xs font-bold tabular-nums text-ink-2">
                      {stageLeads.length}
                    </span>
                  </div>

                  <div className="flex-1 space-y-3">
                    {stageLeads.length === 0 ? (
                      <div className="flex h-full min-h-[100px] items-center justify-center rounded-xl border-2 border-dashed border-line p-4">
                        <span className="text-center text-xs font-medium text-slate-400">No leads in this stage</span>
                      </div>
                    ) : (
                      stageLeads.map((lead) => (
                        <Card key={lead.id} className="space-y-3 p-4">
                          <div className="flex items-start gap-3">
                            <Avatar name={lead.name} size={32} />
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold leading-tight text-ink">{lead.name}</p>
                              <p className="mt-1 text-[10.5px] font-semibold uppercase tracking-wider text-slate-400">
                                {sourceLabel(lead.source) || 'Unknown Source'}
                              </p>
                            </div>
                          </div>

                          <div className="space-y-1.5 rounded-lg bg-canvas p-2.5 text-xs text-ink-2">
                            <div className="flex items-center gap-2">
                              <Phone className="h-3.5 w-3.5 text-slate-400" />
                              <span className="font-medium tabular-nums">{lead.phone}</span>
                            </div>
                            {lead.email && (
                              <div className="flex items-center gap-2 truncate">
                                <Mail className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                                <span className="truncate">{lead.email}</span>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center justify-between gap-2 pt-0.5">
                            {stageSelect(lead, true)}
                            {!isConverted(lead) && !isLost(lead) && canConvertLead && convertButton(lead, true)}
                          </div>
                          {lostReasonNote(lead)}
                        </Card>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Add Lead Drawer */}
        <AddLeadSlideOver isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />
        <LostReasonSlideOver
          lead={lostLead}
          saving={updateStage.isPending}
          onClose={() => setLostLead(null)}
          onSave={handleLostSave}
        />
      </div>
    </AppShell>
  );
}
