'use client';

import React, { useState } from 'react';
import { Plus, Stethoscope, Phone, Mail, Award, X, Edit3, Trash2, IndianRupee, User } from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { Therapist } from '@/types/crm';
import { toast } from 'sonner';

export const TherapistsView: React.FC = () => {
  const { therapists, addTherapist, updateTherapist, deleteTherapist } = useCRMStore();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTherapist, setEditingTherapist] = useState<Therapist | null>(null);

  const [name, setName] = useState('');
  const [specialization, setSpecialization] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [regNo, setRegNo] = useState('');
  const [salary, setSalary] = useState<number | ''>('');
  const [qualification, setQualification] = useState('');
  const [notes, setNotes] = useState('');

  const openAddModal = () => {
    setEditingTherapist(null);
    setName('');
    setSpecialization('');
    setMobile('');
    setEmail('');
    setRegNo('');
    setSalary('');
    setQualification('');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (t: Therapist) => {
    setEditingTherapist(t);
    setName(t.name);
    setSpecialization(t.specialization || '');
    setMobile(t.mobile || '');
    setEmail(t.email || '');
    setRegNo(t.regNo || '');
    setSalary(t.salary || '');
    setQualification(t.qualification || '');
    setNotes(t.notes || '');
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('Please enter the therapist name');
      return;
    }

    if (editingTherapist) {
      updateTherapist(editingTherapist.id, {
        name: name.trim(),
        specialization: specialization.trim() || undefined,
        mobile: mobile.trim() || undefined,
        email: email.trim() || undefined,
        regNo: regNo.trim() || undefined,
        salary: salary === '' ? undefined : Number(salary),
        qualification: qualification.trim() || undefined,
        notes: notes.trim() || undefined
      });
      toast.success('Therapist profile updated successfully');
    } else {
      addTherapist({
        name: name.trim(),
        specialization: specialization.trim() || undefined,
        mobile: mobile.trim() || undefined,
        email: email.trim() || undefined,
        regNo: regNo.trim() || undefined,
        salary: salary === '' ? undefined : Number(salary),
        qualification: qualification.trim() || undefined,
        notes: notes.trim() || undefined
      });
      toast.success('Therapist profile added successfully');
    }

    setIsModalOpen(false);
  };

  const totalMonthlySalary = therapists.reduce((sum, t) => sum + (t.salary || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-[#16213A] border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-extrabold text-base text-[var(--foreground)]">Therapist & Medical Staff Directory</h3>
            <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-[var(--teal)]/10 text-[var(--teal)] border border-[var(--teal)]/20">
              {therapists.length} Active Staff
            </span>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-400 mt-1">
            Therapist profiles automatically populate appointment scheduling options and monthly staff payroll calculations.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="hidden md:flex flex-col text-right pr-3 border-r border-slate-200 dark:border-slate-800">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Total Monthly Payroll</span>
            <span className="text-sm font-extrabold text-emerald-600">₹{totalMonthlySalary.toLocaleString('en-IN')}</span>
          </div>

          <button
            onClick={openAddModal}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-95 transition-all shadow-md hover:-translate-y-0.5 active:translate-y-0"
          >
            <Plus className="w-4 h-4" />
            Add Therapist / Doctor
          </button>
        </div>
      </div>

      {/* Staff Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {therapists.map((t) => (
          <div
            key={t.id}
            className="glass-card p-5 rounded-2xl space-y-4 hover-lift relative flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-2xl bg-[var(--navy)]/10 dark:bg-[#48CAE4]/10 text-[var(--navy)] dark:text-[#48CAE4]">
                    <Stethoscope className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm text-[var(--foreground)]">{t.name}</h4>
                    <p className="text-xs font-semibold text-[var(--teal)]">{t.specialization || 'General Physiotherapist'}</p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEditModal(t)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-[var(--foreground)] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      deleteTherapist(t.id);
                      toast.success('Therapist profile deleted');
                    }}
                    className="p-1.5 rounded-lg text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                {t.mobile && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="font-medium text-[var(--foreground)]">{t.mobile}</span>
                  </div>
                )}
                {t.email && (
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{t.email}</span>
                  </div>
                )}
                {t.regNo && (
                  <div className="flex items-center gap-2">
                    <Award className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>Reg: {t.regNo}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Monthly Compensation</span>
              <span className="font-extrabold text-[var(--foreground)]">
                {t.salary ? `₹${t.salary.toLocaleString('en-IN')}` : 'Not Specified'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Solid Opaque Add / Edit Therapist Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-lg p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h2 className="text-base font-extrabold text-[var(--foreground)]">
                {editingTherapist ? 'Edit Therapist Profile' : 'Add Therapist / Doctor'}
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
                  placeholder="e.g. Dr. Ramesh Sharma"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Clinical Specialization
                </label>
                <input
                  type="text"
                  value={specialization}
                  onChange={(e) => setSpecialization(e.target.value)}
                  placeholder="Senior Physiotherapist, Neuro Rehabilitation..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Mobile Number
                  </label>
                  <input
                    type="tel"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    placeholder="9876543210"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="doctor@clinic.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Registration No.
                  </label>
                  <input
                    type="text"
                    value={regNo}
                    onChange={(e) => setRegNo(e.target.value)}
                    placeholder="PT-2024-8891"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                    Monthly Salary (₹)
                  </label>
                  <input
                    type="number"
                    value={salary}
                    onChange={(e) => setSalary(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="45000"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 text-sm focus:outline-none focus:border-[var(--teal)] transition-colors"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
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
                  {editingTherapist ? 'Update Profile' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default TherapistsView;
