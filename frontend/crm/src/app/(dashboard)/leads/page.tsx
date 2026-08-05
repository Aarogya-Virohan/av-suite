'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { useLeads, useUpdateLeadStage, useConvertLead } from '../../../features/leads/api';
import { AddLeadSlideOver } from '../../../features/leads/components/AddLeadSlideOver';
import { Lead, LeadStage } from '../../../types/api';
import { Plus, UserCheck, ArrowRight, Phone, Mail } from 'lucide-react';
import { toast } from 'sonner';

const STAGES: { key: LeadStage; label: string; color: string }[] = [
  { key: 'new', label: 'New', color: 'bg-blue-500' },
  { key: 'contacted', label: 'Contacted', color: 'bg-amber-500' },
  { key: 'qualified', label: 'Qualified', color: 'bg-purple-500' },
  { key: 'converted', label: 'Converted', color: 'bg-emerald-500' },
  { key: 'lost', label: 'Lost', color: 'bg-slate-400' },
];

export default function LeadsPage() {
  const { data: leads = [], isLoading } = useLeads();
  const updateStage = useUpdateLeadStage();
  const convertLead = useConvertLead();
  const [isAddOpen, setIsAddOpen] = useState(false);

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
    try {
      await updateStage.mutateAsync({ id: leadId, stage: newStage });
      toast.success('Lead stage updated');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Leads Kanban</h1>
            <p className="text-sm text-slate-500">Track and convert prospective patients</p>
          </div>
          <button
            onClick={() => setIsAddOpen(true)}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm rounded-lg flex items-center gap-2 transition-colors cursor-pointer shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Lead</span>
          </button>
        </div>

        {/* Kanban Board */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 items-start">
          {STAGES.map((stage) => {
            const stageLeads = leads.filter((l) => l.stage === stage.key);
            return (
              <div
                key={stage.key}
                className="bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3 space-y-3 min-h-[400px]"
              >
                {/* Column Header */}
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2 px-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${stage.color}`} />
                    <span className="font-bold text-xs uppercase tracking-wider text-slate-700 dark:text-slate-200">
                      {stage.label}
                    </span>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {stageLeads.length}
                  </span>
                </div>

                {/* Lead Cards */}
                <div className="space-y-2.5">
                  {stageLeads.map((lead) => (
                    <div
                      key={lead.id}
                      className="p-3.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xs space-y-2"
                    >
                      <p className="font-bold text-sm text-slate-900 dark:text-white">{lead.name}</p>
                      <div className="space-y-1 text-xs text-slate-500">
                        <div className="flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5 text-slate-400" />
                          <span>{lead.phone}</span>
                        </div>
                        {lead.email && (
                          <div className="flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-slate-400" />
                            <span className="truncate">{lead.email}</span>
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-100 dark:border-slate-900 flex items-center justify-between">
                        <select
                          value={lead.stage}
                          onChange={(e) => handleStageChange(lead.id, e.target.value as LeadStage)}
                          className="text-[11px] bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded px-1.5 py-1 text-slate-700 dark:text-slate-300"
                        >
                          {STAGES.map((s) => (
                            <option key={s.key} value={s.key}>
                              Move to {s.label}
                            </option>
                          ))}
                        </select>

                        {lead.stage !== 'converted' && (
                          <button
                            onClick={() => handleConvert(lead.id, lead.name)}
                            className="px-2 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 cursor-pointer"
                          >
                            <UserCheck className="w-3 h-3" />
                            <span>Convert</span>
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Add Lead Drawer */}
        <AddLeadSlideOver isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />
      </div>
    </AppShell>
  );
}
