'use client';

import React, { useState } from 'react';
import { Trash2, RotateCcw, ShieldAlert } from 'lucide-react';
import { useCRMStore } from '@/lib/store';

export const RecycleBinView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'patients' | 'appointments' | 'invoices' | 'leads'>('patients');
  const { recycleBin, restoreFromRecycleBin, permanentlyDeleteFromRecycleBin } = useCRMStore();

  const filteredItems = recycleBin.filter((item) => item.type === activeTab);

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-600 flex items-center gap-3">
        <ShieldAlert className="w-5 h-5 shrink-0" />
        <div>
          <p className="font-bold">Soft-Deleted Items Storage</p>
          <p>Items in the Recycle Bin are safely preserved and can be restored anytime within 30 days.</p>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="flex border-b border-[var(--border)] gap-2 text-xs font-bold">
        {[
          { id: 'patients', label: 'Patients' },
          { id: 'appointments', label: 'Appointments' },
          { id: 'invoices', label: 'Invoices' },
          { id: 'leads', label: 'Leads' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2.5 border-b-2 transition-colors uppercase tracking-wider ${
              activeTab === tab.id
                ? 'border-[var(--teal)] text-[var(--teal)]'
                : 'border-transparent text-[var(--text-light)] hover:text-[var(--text)]'
            }`}
          >
            {tab.label} (
            {recycleBin.filter((i) => i.type === tab.id).length})
          </button>
        ))}
      </div>

      {/* Deleted Items List */}
      <div className="space-y-3">
        {filteredItems.length === 0 ? (
          <div className="text-center py-12 text-xs text-[var(--text-light)] bg-[var(--card-bg)] border border-[var(--border)] rounded-xl">
            No deleted {activeTab} in the bin.
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl shadow-sm flex items-center justify-between gap-4 text-xs"
            >
              <div>
                <p className="font-bold text-sm text-[var(--text)]">
                  {item.data.name || item.data.patientName || item.data.id || 'Deleted Item'}
                </p>
                <p className="text-[var(--text-light)] mt-0.5">
                  Deleted on: {new Date(item.deletedAt).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => restoreFromRecycleBin(item.id)}
                  className="px-3 py-1.5 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90 inline-flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Restore
                </button>
                <button
                  onClick={() => permanentlyDeleteFromRecycleBin(item.id)}
                  className="px-3 py-1.5 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 inline-flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Permanently Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
