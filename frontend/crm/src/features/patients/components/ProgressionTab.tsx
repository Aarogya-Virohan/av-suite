'use client';

import React from 'react';
import { toast } from 'sonner';
import { useTreatments } from '../../treatments/api';
import { useAssessments } from '../../assessments/api';
import { TrendingDown, FileText, Download, Activity } from 'lucide-react';
import { apiClient } from '../../../lib/api-client';

export function ProgressionTab({ patientId }: { patientId: string }) {
  const { data: treatmentsResponse } = useTreatments(patientId);
  const sessions = treatmentsResponse?.data || [];
  
  const { data: assessmentsResponse } = useAssessments(patientId);
  const assessments = assessmentsResponse?.data || [];

  const painScores = sessions
    .filter((s: any) => s.pain_score != null)
    .map((s: any) => s.pain_score as number);

  const initialPain = painScores.length > 0 ? painScores[0] : null;
  const currentPain = painScores.length > 0 ? painScores[painScores.length - 1] : null;
  const painChange = initialPain !== null && currentPain !== null ? initialPain - currentPain : null;

  const handleExportPdf = async () => {
    try {
      toast.info('Generating Progression PDF...');
      await apiClient.get(`/documents/${patientId}/download`);
      toast.success('Progression PDF exported successfully!');
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  // Get the first and last assessment for comparison
  const baselineAssessment = assessments.length > 0 ? assessments[assessments.length - 1] : null;
  const latestAssessment = assessments.length > 1 ? assessments[0] : null;

  return (
    <div className="space-y-6">
      {/* Header & Export Action */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Clinical Progression</h3>
          <p className="text-xs text-slate-500">Track pain reduction & functional improvements over time</p>
        </div>
        <button
          onClick={handleExportPdf}
          className="px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 cursor-pointer shadow-xs"
        >
          <Download className="w-4 h-4" />
          <span>Export Progression PDF</span>
        </button>
      </div>

      {/* Progression Stats Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-center">
          <p className="text-xl font-extrabold text-slate-900 dark:text-white">{sessions.length}</p>
          <p className="text-[10px] font-bold uppercase text-slate-400 mt-1">Total Sessions</p>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-center">
          <p className="text-xl font-extrabold text-slate-900 dark:text-white">{assessments.length}</p>
          <p className="text-[10px] font-bold uppercase text-slate-400 mt-1">Assessments</p>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-center">
          <p className="text-xl font-extrabold text-rose-500">{initialPain !== null ? `${initialPain}/10` : 'N/A'}</p>
          <p className="text-[10px] font-bold uppercase text-slate-400 mt-1">Initial Pain</p>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-center">
          <p className="text-xl font-extrabold text-emerald-600">{currentPain !== null ? `${currentPain}/10` : 'N/A'}</p>
          <p className="text-[10px] font-bold uppercase text-slate-400 mt-1">Current Pain</p>
        </div>

        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl text-center col-span-2 md:col-span-1">
          <p className="text-xl font-extrabold text-emerald-600 flex items-center justify-center gap-1">
            <TrendingDown className="w-5 h-5" /> {painChange !== null ? `▼ ${painChange} pts` : 'N/A'}
          </p>
          <p className="text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-300 mt-1">
            Pain Reduction
          </p>
        </div>
      </div>

      {/* Baseline vs Latest Re-Assessment Comparison */}
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
        <h4 className="text-sm font-bold text-slate-900 dark:text-white">
          Baseline vs. Latest Re-Assessment Comparison
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          
          <div className="p-4 bg-slate-50 dark:bg-slate-950 border rounded-lg space-y-2">
            <p className="font-bold text-teal-600 uppercase text-[10px]">Initial Baseline Assessment</p>
            {baselineAssessment ? (
              <>
                <p><strong>Subjective:</strong> {baselineAssessment.form_data?.subjective || 'No data recorded.'}</p>
                <p><strong>Objective:</strong> {baselineAssessment.form_data?.objective || 'No data recorded.'}</p>
                <p><strong>Assessment:</strong> {baselineAssessment.form_data?.assessment || baselineAssessment.diagnosis || 'No data recorded.'}</p>
              </>
            ) : (
              <p className="text-slate-500 italic">No baseline assessment recorded yet.</p>
            )}
          </div>

          <div className="p-4 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 rounded-lg space-y-2">
            <p className="font-bold text-emerald-600 uppercase text-[10px]">Latest Re-Assessment</p>
            {latestAssessment ? (
              <>
                <p><strong>Subjective:</strong> {latestAssessment.form_data?.subjective || 'No data recorded.'}</p>
                <p><strong>Objective:</strong> {latestAssessment.form_data?.objective || 'No data recorded.'}</p>
                <p><strong>Assessment:</strong> {latestAssessment.form_data?.assessment || latestAssessment.diagnosis || 'No data recorded.'}</p>
              </>
            ) : (
              <p className="text-slate-500 italic">No re-assessments recorded yet.</p>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}
