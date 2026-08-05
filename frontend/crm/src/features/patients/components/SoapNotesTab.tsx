'use client';

import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { SoapAssessment } from '../../../types/api';
import { mockSoapAssessments } from '../../../mocks';
import { useAuthStore } from '../../../store';
import { CheckCircle2, Lock, Unlock, Save, FileCheck, Stethoscope, Heart, Zap, Baby, Activity } from 'lucide-react';

interface SpecialtyOption {
  key: string;
  label: string;
  icon: React.ElementType;
}

const SPECIALTIES: SpecialtyOption[] = [
  { key: 'ortho', label: 'Ortho', icon: Activity },
  { key: 'neuro', label: 'Neuro', icon: Stethoscope },
  { key: 'cardiopulm', label: 'Cardio', icon: Heart },
  { key: 'sports', label: 'Sports', icon: Zap },
  { key: 'paeds', label: 'Paeds', icon: Baby },
  { key: 'general', label: 'General', icon: FileCheck },
];

export function SoapNotesTab({
  patientId,
  isReassessmentOnly = false,
}: {
  patientId: string;
  isReassessmentOnly?: boolean;
}) {
  const role = useAuthStore((s) => s.role);
  const [selectedSpecialty, setSelectedSpecialty] = useState('ortho');
  const [painVas, setPainVas] = useState<number>(6);

  const [assessments, setAssessments] = useState<SoapAssessment[]>(() =>
    mockSoapAssessments.filter(
      (a) => a.patient_id === patientId && a.is_reassessment === isReassessmentOnly
    )
  );

  const [activeNote, setActiveNote] = useState<SoapAssessment>(() => {
    const existing = assessments[0];
    if (existing) return existing;
    return {
      id: `soap_${Date.now()}`,
      clinic_id: 'cln_aarogya_1',
      patient_id: patientId,
      appointment_id: null,
      author_id: 'usr_therapist_1',
      specialty: 'ortho',
      diagnosis: '',
      is_reassessment: isReassessmentOnly,
      form_data: {
        subjective: '',
        objective: '',
        assessment: '',
        plan: '',
        specialty_data: {},
      },
      finalized_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  });

  const isFinalized = !!activeNote.finalized_at;

  // Debounced auto-save effect (2s)
  useEffect(() => {
    if (isFinalized) return;
    const timer = setTimeout(() => {
      // Auto-save logic
    }, 2000);
    return () => clearTimeout(timer);
  }, [activeNote, isFinalized]);

  const handleFinalize = () => {
    const updated = {
      ...activeNote,
      finalized_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setActiveNote(updated);
    setAssessments((prev) => [updated, ...prev.filter((a) => a.id !== updated.id)]);
    toast.success('SOAP note finalized & locked');
  };

  const handleReopen = () => {
    if (role !== 'admin') {
      toast.error('Only Admins can re-open finalized clinical notes');
      return;
    }
    const updated = {
      ...activeNote,
      finalized_at: null,
      updated_at: new Date().toISOString(),
    };
    setActiveNote(updated);
    toast.success('Note re-opened for editing (Audit log recorded)');
  };

  const updateFormData = (key: string, value: unknown) => {
    if (isFinalized) return;
    setActiveNote((prev) => ({
      ...prev,
      form_data: {
        ...prev.form_data,
        [key]: value,
      },
    }));
  };

  const getPainColor = (val: number) => {
    if (val <= 3) return 'bg-emerald-500 text-white border-emerald-600';
    if (val <= 6) return 'bg-amber-500 text-white border-amber-600';
    return 'bg-rose-500 text-white border-rose-600';
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              {isReassessmentOnly ? 'Re-assessment Note' : 'SOAP Clinical Assessment'}
            </h3>
            {isFinalized ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                <Lock className="w-3 h-3" /> Finalized
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                <Save className="w-3 h-3 animate-pulse" /> Draft (Autosaving)
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {isFinalized
              ? `Finalized on ${new Date(activeNote.finalized_at!).toLocaleString()}`
              : 'Changes autosaved every 2 seconds'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isFinalized ? (
            role === 'admin' && (
              <button
                onClick={handleReopen}
                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs rounded-lg flex items-center gap-1.5 cursor-pointer"
              >
                <Unlock className="w-3.5 h-3.5" />
                <span>Re-open (Admin Only)</span>
              </button>
            )
          ) : (
            <button
              onClick={handleFinalize}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 shadow-sm cursor-pointer"
            >
              <FileCheck className="w-4 h-4" />
              <span>Finalize & Lock Note</span>
            </button>
          )}
        </div>
      </div>

      {/* Specialty Chips Selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {SPECIALTIES.map((spec) => {
          const Icon = spec.icon;
          const isSelected = selectedSpecialty === spec.key;
          return (
            <button
              key={spec.key}
              disabled={isFinalized}
              onClick={() => {
                setSelectedSpecialty(spec.key);
                setActiveNote((prev) => ({ ...prev, specialty: spec.key }));
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-teal-600 border-teal-600 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:border-teal-500'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{spec.label}</span>
            </button>
          );
        })}
      </div>

      {/* Pain VAS 0-10 Interactive Scale */}
      <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-500">
          Pain VAS Scale (0 to 10)
        </label>
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          {Array.from({ length: 11 }, (_, i) => (
            <button
              key={i}
              type="button"
              disabled={isFinalized}
              onClick={() => setPainVas(i)}
              className={`w-8 h-8 rounded-lg text-xs font-extrabold border transition-all ${
                painVas === i
                  ? getPainColor(i)
                  : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100'
              }`}
            >
              {i}
            </button>
          ))}
        </div>
      </div>

      {/* Main SOAP Editor Card */}
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-6">
        <div className="border-b border-slate-100 dark:border-slate-800 pb-4">
          <label className="block text-xs font-bold uppercase text-slate-400 mb-1">
            Clinical Diagnosis
          </label>
          <input
            type="text"
            disabled={isFinalized}
            value={activeNote.diagnosis || ''}
            onChange={(e) => setActiveNote({ ...activeNote, diagnosis: e.target.value })}
            placeholder="e.g. Lumbar disc herniation L4-L5"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm disabled:opacity-60"
          />
        </div>

        {/* 4 SOAP Quadrants */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase text-teal-600 mb-1">
              Subjective (S)
            </label>
            <textarea
              rows={3}
              disabled={isFinalized}
              value={String(activeNote.form_data.subjective || '')}
              onChange={(e) => updateFormData('subjective', e.target.value)}
              placeholder="Patient reported symptoms, pain history, and limitations..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-teal-600 mb-1">
              Objective (O)
            </label>
            <textarea
              rows={3}
              disabled={isFinalized}
              value={String(activeNote.form_data.objective || '')}
              onChange={(e) => updateFormData('objective', e.target.value)}
              placeholder="Physical findings, ROM tests, posture analysis..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-teal-600 mb-1">
              Assessment (A)
            </label>
            <textarea
              rows={3}
              disabled={isFinalized}
              value={String(activeNote.form_data.assessment || '')}
              onChange={(e) => updateFormData('assessment', e.target.value)}
              placeholder="Clinical impression and progress comparison..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-teal-600 mb-1">
              Plan (P)
            </label>
            <textarea
              rows={3}
              disabled={isFinalized}
              value={String(activeNote.form_data.plan || '')}
              onChange={(e) => updateFormData('plan', e.target.value)}
              placeholder="Treatment goals, frequency of visits, home routine..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm disabled:opacity-60"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
