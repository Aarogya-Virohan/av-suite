'use client';

import React from 'react';
import { Eye, MessageCircle, Trash2 } from 'lucide-react';
import { Patient } from '@/types/crm';

interface PatientTableProps {
  patients: Patient[];
  onOpenDashboard: (p: Patient) => void;
  onWhatsApp: (mobile: string, name: string) => void;
  onDelete: (id: string) => void;
}

export const PatientTable: React.FC<PatientTableProps> = ({
  patients,
  onOpenDashboard,
  onWhatsApp,
  onDelete
}) => {
  return (
    <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-[#1C2541] shadow-sm">
      <table className="w-full text-left border-collapse text-xs clinical-table">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-slate-400">
            <th className="p-4">Patient Name</th>
            <th className="p-4">Mobile</th>
            <th className="p-4">Age / Gender</th>
            <th className="p-4">Diagnosis</th>
            <th className="p-4">Status</th>
            <th className="p-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50 text-[var(--foreground)]">
          {patients.map((p) => (
            <tr
              key={p.id}
              className="hover:bg-slate-50/40 dark:hover:bg-slate-900/10 transition-colors"
            >
              <td className="p-4 font-bold text-sm text-[var(--navy)] dark:text-[#48CAE4] cursor-pointer" onClick={() => onOpenDashboard(p)}>
                {p.name}
              </td>
              <td className="p-4 font-semibold text-slate-600 dark:text-slate-300">{p.mobile}</td>
              <td className="p-4 text-slate-500 dark:text-slate-400">
                {p.age ? `${p.age} yrs` : '—'} / {p.gender || '—'}
              </td>
              <td className="p-4 max-w-xs truncate text-slate-600 dark:text-slate-300">
                {p.diagnosis || '—'}
              </td>
              <td className="p-4">
                <span
                  className={`px-2.5 py-1 text-[10px] font-bold rounded-full border ${
                    p.status === 'Active'
                      ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                      : p.status === 'Discharged'
                      ? 'bg-slate-150 text-slate-600 border-slate-200'
                      : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                  }`}
                >
                  {p.status}
                </span>
              </td>
              <td className="p-4 text-right">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => onOpenDashboard(p)}
                    className="p-2 rounded-xl border border-slate-250 hover:bg-[var(--teal)] hover:text-white transition-all hover:scale-105"
                    title="Open Clinical Dashboard"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onWhatsApp(p.mobile, p.name)}
                    className="p-2 rounded-xl bg-emerald-500 text-white hover:bg-emerald-600 transition-all hover:scale-105"
                    title="Send WhatsApp Message"
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                  </button>
                  {/*
                    TODO: Enable when backend implements PATCH/DELETE patients endpoints.
                    <button
                      onClick={() => onDelete(p.id)}
                      className="p-2 rounded-xl border border-slate-250 text-red-500 hover:bg-red-500/10 transition-all"
                      title="Move to Recycle Bin"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  */}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
export default PatientTable;
