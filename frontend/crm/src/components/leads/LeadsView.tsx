'use client';

import React, { useState } from 'react';
import { Plus, UserCheck, X, ArrowRight, MessageCircle, Trash2, Edit3, Tag } from 'lucide-react';
import { Lead, LeadStage } from '@/types/crm';
import { toast } from 'sonner';
import { useLeads, useCreateLead, useUpdateLead, useConvertLead } from '@/features/leads/hooks/useLeads';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const LEAD_STAGES: LeadStage[] = [
  'New Lead',
  'Contacted',
  'Appointment Booked',
  'Converted',
  'Lost'
];

export const LeadsView: React.FC = () => {
  const { data: leads = [], isLoading, isError, refetch } = useLeads();
  const createMutation = useCreateLead();
  const updateMutation = useUpdateLead();
  const convertMutation = useConvertLead();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);

  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [source, setSource] = useState('Google');
  const [stage, setStage] = useState<LeadStage>('New Lead');
  const [notes, setNotes] = useState('');

  const openAddModal = () => {
    setEditingLead(null);
    setName('');
    setMobile('');
    setSource('Google');
    setStage('New Lead');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (lead: Lead) => {
    setEditingLead(lead);
    setName(lead.name);
    setMobile(lead.mobile || '');
    setSource(lead.source);
    setStage(lead.stage);
    setNotes(lead.notes || '');
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('Please enter the prospect name');
      return;
    }

    if (editingLead) {
      updateMutation.mutate({
        id: editingLead.id,
        data: {
          name: name.trim(),
          mobile: mobile.trim() || undefined,
          source,
          stage,
          notes: notes.trim() || undefined
        }
      });
    } else {
      createMutation.mutate({
        name: name.trim(),
        mobile: mobile.trim() || undefined,
        source,
        stage,
        notes: notes.trim() || undefined,
        clinic_id: 'default_clinic' // Usually backend derives this or it's provided
      } as any);
    }

    setIsModalOpen(false);
  };

  const handleWhatsApp = (mobile?: string, nameStr?: string) => {
    if (!mobile) return;
    const cleanMobile = mobile.replace(/\D/g, '');
    const num = cleanMobile.startsWith('91') ? cleanMobile : `91${cleanMobile}`;
    const msg = encodeURIComponent(`Hi ${nameStr || 'there'}, greeting from Aarogya Virohan. How can we assist with your health goals?`);
    window.open(`https://wa.me/${num}?text=${msg}`, '_blank');
  };

  const handleConvert = (leadId: string, leadName: string) => {
    convertMutation.mutate(leadId);
  };

  return (
    <div className="space-y-6">
      {/* Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-[#16213A] border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-extrabold text-base text-[var(--foreground)]">Patient Acquisition & Lead Pipeline</h3>
            <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-[var(--teal)]/10 text-[var(--teal)] border border-[var(--teal)]/20">
              {leads.length} Prospects
            </span>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-400 mt-1">
            Track patient inquiries across conversion stages and onboard prospects seamlessly into clinical care.
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-95 transition-all shadow-md hover:-translate-y-0.5 active:translate-y-0"
        >
          <Plus className="w-4 h-4" />
          Add Prospect Lead
        </button>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : leads.length === 0 ? (
        <EmptyState
          title="No Leads Found"
          description="Start building your patient pipeline by adding prospect leads."
          actionLabel="Add First Lead"
          onAction={openAddModal}
        />
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {LEAD_STAGES.map((colStage) => {
          const colLeads = leads.filter((l) => l.stage === colStage);
          return (
            <div
              key={colStage}
              className="bg-slate-50/70 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-4 min-w-[280px] flex-1 flex flex-col space-y-3"
            >
              {/* Column Header */}
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2.5">
                <span className="font-extrabold text-xs text-[var(--foreground)] uppercase tracking-wider">
                  {colStage}
                </span>
                <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-full bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  {colLeads.length}
                </span>
              </div>

              {/* Lead Cards List */}
              <div className="space-y-3 flex-1 overflow-y-auto max-h-[60vh]">
                {colLeads.length === 0 ? (
                  <div className="p-4 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-[11px] text-slate-400">
                    No prospects in stage
                  </div>
                ) : (
                  colLeads.map((lead) => (
                    <div
                      key={lead.id}
                      className="glass-card p-4 rounded-xl space-y-2.5 hover-lift relative group"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-extrabold text-xs text-[var(--foreground)]">{lead.name}</h4>
                          {lead.mobile && (
                            <p className="text-[11px] text-slate-400 font-medium">{lead.mobile}</p>
                          )}
                        </div>

                        <span className="px-2 py-0.5 text-[9px] font-bold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                          {lead.source}
                        </span>
                      </div>

                      {lead.notes && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 italic line-clamp-2">
                          "{lead.notes}"
                        </p>
                      )}

                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px]">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openEditModal(lead)}
                            className="p-1 rounded text-slate-400 hover:text-[var(--foreground)] transition-colors"
                            title="Edit Lead"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          {lead.mobile && (
                            <button
                              onClick={() => handleWhatsApp(lead.mobile, lead.name)}
                              className="p-1 rounded text-emerald-500 hover:text-emerald-600 transition-colors"
                              title="WhatsApp Message"
                            >
                              <MessageCircle className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>

                        {lead.stage !== 'Converted' ? (
                          <button
                            onClick={() => handleConvert(lead.id, lead.name)}
                            className="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500 hover:text-white transition-all inline-flex items-center gap-1"
                          >
                            <UserCheck className="w-3 h-3" />
                            Convert
                          </button>
                        ) : (
                          <span className="px-2 py-0.5 text-[9px] font-bold rounded-md bg-emerald-500 text-white">
                            Converted
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}

      {/* Solid Opaque Add / Edit Lead Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-lg p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h2 className="text-base font-extrabold text-[var(--foreground)]">
                {editingLead ? 'Edit Prospect Lead' : 'Add New Prospect Lead'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-[var(--foreground)] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs font-semibold">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Amitabh Verma"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Mobile Number (10 Digits)
                </label>
                <input
                  type="tel"
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  placeholder="e.g. 9988776655"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Acquisition Source
                  </label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
                  >
                    <option value="Google">Google</option>
                    <option value="Instagram">Instagram</option>
                    <option value="Facebook">Facebook</option>
                    <option value="Referral">Referral</option>
                    <option value="Walk In">Walk In</option>
                    <option value="WhatsApp">WhatsApp</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Pipeline Stage
                  </label>
                  <select
                    value={stage}
                    onChange={(e) => setStage(e.target.value as LeadStage)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] font-semibold"
                  >
                    {LEAD_STAGES.map((stg) => (
                      <option key={stg} value={stg}>
                        {stg}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Inquiry Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Patient inquiry details, pain symptoms, preferred appointment times..."
                  rows={3}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
                {editingLead ? (
                  <button
                    type="button"
                    onClick={() => {
                      deleteLead(editingLead.id);
                      setIsModalOpen(false);
                      toast.success('Lead deleted');
                    }}
                    className="text-red-500 hover:underline font-bold text-xs"
                  >
                    Delete Lead
                  </button>
                ) : (
                  <div />
                )}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-5 py-2.5 border border-slate-200 dark:border-slate-800 rounded-xl text-[var(--foreground)] font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-6 py-2.5 bg-[var(--navy)] text-white font-bold rounded-xl hover:opacity-95 transition-all shadow-md"
                  >
                    {editingLead ? 'Update Lead' : 'Save Prospect'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default LeadsView;
