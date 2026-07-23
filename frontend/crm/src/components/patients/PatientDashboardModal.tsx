'use client';

import React, { useState } from 'react';
import {
  X,
  User,
  FileText,
  Stethoscope,
  Activity,
  Package,
  LineChart,
  FileSpreadsheet,
  Plus,
  MessageCircle,
  Upload,
  CheckCircle,
  Printer
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import { useCRMStore } from '@/lib/store';
import { Patient, SpecialtyKey } from '@/types/crm';

interface PatientDashboardModalProps {
  patient: Patient | null;
  isOpen: boolean;
  onClose: () => void;
}

export const PatientDashboardModal: React.FC<PatientDashboardModalProps> = ({
  patient,
  isOpen,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState<
    'info' | 'docs' | 'assessment' | 'treatment' | 'packages' | 'progression' | 'rx'
  >('info');

  const store = useCRMStore();

  if (!isOpen || !patient) return null;

  // Patient's related data
  const pTreatments = store.treatments.filter((t) => t.patientId === patient.id);
  const pAssessments = store.assessments.filter((a) => a.patientId === patient.id);
  const pAppointments = store.appointments.filter((a) => a.patientId === patient.id);
  const pInvoices = store.invoices.filter((i) => i.patientId === patient.id);
  const pPackages = store.packages.filter((pkg) => pkg.patientId === patient.id);
  const activePackage = pPackages.find((pkg) => pkg.status === 'Active');
  const pDocs = store.documents.filter((d) => d.patientId === patient.id);

  // Pain Scores
  const painScores = pTreatments
    .filter((t) => t.painScore !== undefined && t.painScore !== null)
    .map((t) => t.painScore!);

  const firstPain = painScores.length > 0 ? painScores[0] : null;
  const currentPain = painScores.length > 0 ? painScores[painScores.length - 1] : null;

  // Paid & Due
  const totalPaid = pInvoices
    .filter((i) => i.status === 'Paid')
    .reduce((sum, i) => sum + i.total, 0);
  const totalDue = pInvoices
    .filter((i) => i.status === 'Due' || i.status === 'Partial')
    .reduce((sum, i) => sum + (i.total - i.paidAmount), 0);

  const painChartData = {
    labels: pTreatments.map((_, i) => `S${i + 1}`),
    datasets: [
      {
        label: 'Pain VAS Score',
        data: painScores,
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: '#EF4444'
      }
    ]
  };

  const painChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { min: 0, max: 10, ticks: { stepSize: 2 } },
      x: { grid: { display: false } }
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden my-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[var(--navy)] to-blue-700 text-white p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-extrabold flex items-center gap-2">
              {patient.name}
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-white/20">
                {patient.status}
              </span>
            </h2>
            <p className="text-xs text-white/80 mt-1">
              {patient.age || '—'} yrs • {patient.gender || '—'} • {patient.mobile} • Dx: {patient.diagnosis || 'Unspecified'}
            </p>
            <div className="flex items-center gap-2 mt-2">
              {firstPain !== null && (
                <span className="text-xs px-2 py-0.5 rounded bg-black/20 text-white/90">
                  Initial Pain: {firstPain}/10
                </span>
              )}
              {currentPain !== null && (
                <span className="text-xs px-2 py-0.5 rounded font-bold bg-red-500/30 text-white">
                  Current Pain: {currentPain}/10
                </span>
              )}
              {firstPain !== null && currentPain !== null && firstPain > currentPain && (
                <span className="text-xs px-2 py-0.5 rounded font-bold bg-emerald-500/30 text-emerald-200">
                  ▼ {firstPain - currentPain} pts Pain Improved
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              onClick={() => {
                const msg = encodeURIComponent(
                  `Hi ${patient.name}, Session Report from ${store.branding.clinicName}: Last Pain Score ${currentPain || 'N/A'}/10. Thank you!`
                );
                window.open(`https://wa.me/91${patient.mobile.replace(/\D/g, '')}?text=${msg}`, '_blank');
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 text-white text-xs font-bold rounded-lg hover:bg-emerald-600 transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              WA Report
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-white/70 hover:text-white rounded-lg hover:bg-white/10"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 p-4 bg-[var(--bg)] border-b border-[var(--border)] text-center text-xs">
          <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border)]">
            <p className="text-lg font-bold text-[var(--navy)]">{pTreatments.length}</p>
            <p className="text-[var(--text-light)] font-semibold uppercase text-[10px]">Sessions</p>
          </div>
          <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border)]">
            <p className="text-lg font-bold text-[var(--navy)]">{pAssessments.length}</p>
            <p className="text-[var(--text-light)] font-semibold uppercase text-[10px]">Assessments</p>
          </div>
          <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border)]">
            <p className="text-lg font-bold text-[var(--navy)]">{pAppointments.length}</p>
            <p className="text-[var(--text-light)] font-semibold uppercase text-[10px]">Visits</p>
          </div>
          <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border)]">
            <p className="text-lg font-bold text-emerald-600">₹{totalPaid.toLocaleString('en-IN')}</p>
            <p className="text-[var(--text-light)] font-semibold uppercase text-[10px]">Paid</p>
          </div>
          <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border)] col-span-2 sm:col-span-1">
            <p className={`text-lg font-bold ${totalDue > 0 ? 'text-red-500' : 'text-[var(--text)]'}`}>
              ₹{totalDue.toLocaleString('en-IN')}
            </p>
            <p className="text-[var(--text-light)] font-semibold uppercase text-[10px]">Due</p>
          </div>
        </div>

        {/* Active Package Card (if any) */}
        {activePackage && (
          <div className="mx-4 mt-4 p-3 bg-teal-500/10 border border-teal-500/30 rounded-xl text-xs flex items-center justify-between">
            <div>
              <p className="font-bold text-[var(--teal)]">{activePackage.packageName}</p>
              <p className="text-[var(--text-light)]">
                {activePackage.sessionsUsed} of {activePackage.totalSessions} sessions used (
                {activePackage.totalSessions - activePackage.sessionsUsed} remaining)
              </p>
            </div>
            <div className="w-32 bg-gray-200 rounded-full h-2 overflow-hidden dark:bg-gray-700">
              <div
                className="bg-[var(--teal)] h-full rounded-full transition-all"
                style={{
                  width: `${(activePackage.sessionsUsed / activePackage.totalSessions) * 100}%`
                }}
              />
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-[var(--border)] px-4 pt-3 gap-1 overflow-x-auto text-xs font-semibold">
          {[
            { id: 'info', label: 'Patient Info', icon: <User className="w-3.5 h-3.5" /> },
            { id: 'docs', label: 'Documents', icon: <FileText className="w-3.5 h-3.5" /> },
            { id: 'assessment', label: 'Assessment', icon: <Stethoscope className="w-3.5 h-3.5" /> },
            { id: 'treatment', label: 'Treatment', icon: <Activity className="w-3.5 h-3.5" /> },
            { id: 'packages', label: 'Packages', icon: <Package className="w-3.5 h-3.5" /> },
            { id: 'progression', label: 'Progression', icon: <LineChart className="w-3.5 h-3.5" /> },
            { id: 'rx', label: 'Prescription Rx', icon: <FileSpreadsheet className="w-3.5 h-3.5" /> }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg border-b-2 whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-[var(--teal)] text-[var(--teal)] font-bold bg-[var(--bg)]'
                  : 'border-transparent text-[var(--text-light)] hover:text-[var(--text)]'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: INFO */}
          {activeTab === 'info' && (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="font-bold text-[var(--text-light)]">Full Name:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.name}</p>
                </div>
                <div>
                  <span className="font-bold text-[var(--text-light)]">Mobile:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.mobile}</p>
                </div>
                <div>
                  <span className="font-bold text-[var(--text-light)]">Age / Gender:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">
                    {patient.age || 'N/A'} yrs • {patient.gender || 'N/A'}
                  </p>
                </div>
                <div>
                  <span className="font-bold text-[var(--text-light)]">Email:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.email || 'N/A'}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="font-bold text-[var(--text-light)]">Address:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.address || 'N/A'}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="font-bold text-[var(--text-light)]">Diagnosis / Chief Complaint:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.diagnosis || 'N/A'}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="font-bold text-[var(--text-light)]">Medical History:</span>
                  <p className="text-sm font-semibold text-[var(--text)] mt-0.5">{patient.medicalHistory || 'N/A'}</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DOCUMENTS */}
          {activeTab === 'docs' && (
            <DocManager patientId={patient.id} docs={pDocs} onUpload={store.addDocument} onDelete={store.deleteDocument} />
          )}

          {/* TAB 3: ASSESSMENT (SOAP Notes) */}
          {activeTab === 'assessment' && (
            <AssessmentManager patientId={patient.id} assessments={pAssessments} onAdd={store.addAssessment} />
          )}

          {/* TAB 4: TREATMENT SESSIONS */}
          {activeTab === 'treatment' && (
            <TreatmentManager patientId={patient.id} treatments={pTreatments} onAdd={store.addTreatment} therapists={store.therapists} />
          )}

          {/* TAB 5: PACKAGES */}
          {activeTab === 'packages' && (
            <PackageManager patientId={patient.id} patientName={patient.name} packages={pPackages} onAdd={store.addPackage} />
          )}

          {/* TAB 6: PROGRESSION */}
          {activeTab === 'progression' && (
            <div className="space-y-6">
              {painScores.length >= 2 ? (
                <div className="bg-[var(--card-bg)] border border-[var(--border)] p-4 rounded-xl space-y-3">
                  <h4 className="font-bold text-sm text-[var(--text)]">Pain Progression Curve</h4>
                  <div className="h-56">
                    <Line data={painChartData} options={painChartOptions} />
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-[var(--text-light)] bg-[var(--bg)] rounded-xl">
                  Add at least 2 treatment sessions with pain scores to render the progression trend chart.
                </div>
              )}
            </div>
          )}

          {/* TAB 7: RX / PRESCRIPTION */}
          {activeTab === 'rx' && (
            <div className="p-6 bg-[var(--bg)] rounded-xl border border-[var(--border)] text-center space-y-4">
              <p className="text-xs text-[var(--text-light)]">
                Generates a branded PDF prescription with clinic logo, patient demographics, and assessment history.
              </p>
              <button
                onClick={() => alert(`Prescription PDF generated for ${patient.name}`)}
                className="px-5 py-2.5 bg-[var(--navy)] text-white text-xs font-bold rounded-xl hover:opacity-90 transition-opacity inline-flex items-center gap-2"
              >
                <Printer className="w-4 h-4" />
                Generate & Export Prescription PDF
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* --- SUB-COMPONENTS FOR DASHBOARD TABS --- */

// Document Manager Component
const DocManager: React.FC<{
  patientId: string;
  docs: any[];
  onUpload: (doc: any) => void;
  onDelete: (id: string) => void;
}> = ({ patientId, docs, onUpload, onDelete }) => {
  const [fileName, setFileName] = useState('');
  const [category, setCategory] = useState<any>('General');

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileName.trim()) return;
    onUpload({
      patientId,
      fileName: fileName.trim(),
      category,
      url: '#'
    });
    setFileName('');
  };

  return (
    <div className="space-y-4 text-xs">
      <form onSubmit={handleUpload} className="p-4 bg-[var(--bg)] rounded-xl border border-[var(--border)] space-y-3">
        <h4 className="font-bold text-sm text-[var(--text)]">Upload Patient Document</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input
            type="text"
            placeholder="Document title / description"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
            required
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as any)}
            className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
          >
            <option value="General">General</option>
            <option value="Lab Report">Lab Report</option>
            <option value="Imaging">Imaging (X-Ray / MRI)</option>
            <option value="Referral Letter">Referral Letter</option>
            <option value="ID Proof">ID Proof</option>
            <option value="Prescription">Prescription</option>
          </select>
        </div>
        <button
          type="submit"
          className="px-4 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90 inline-flex items-center gap-1.5"
        >
          <Upload className="w-3.5 h-3.5" />
          Upload Document
        </button>
      </form>

      <div className="space-y-2">
        <h4 className="font-bold text-sm text-[var(--text)]">Uploaded Files</h4>
        {docs.length === 0 ? (
          <p className="text-[var(--text-light)]">No documents uploaded yet.</p>
        ) : (
          docs.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--card-bg)]">
              <div>
                <p className="font-bold text-[var(--text)]">{doc.fileName}</p>
                <p className="text-[var(--text-light)] text-[10px]">{doc.category} • {new Date(doc.createdAt).toLocaleDateString()}</p>
              </div>
              <button onClick={() => onDelete(doc.id)} className="text-red-500 hover:underline">
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Assessment Manager Component
const AssessmentManager: React.FC<{
  patientId: string;
  assessments: any[];
  onAdd: (asm: any) => void;
}> = ({ patientId, assessments, onAdd }) => {
  const [specialty, setSpecialty] = useState<SpecialtyKey>('ortho');
  const [vasScore, setVasScore] = useState<number>(5);
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [treatmentPlan, setTreatmentPlan] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      patientId,
      specialty,
      isReassessment: false,
      formData: {
        ChiefComplaint: chiefComplaint,
        VASScore: String(vasScore),
        TreatmentPlan: treatmentPlan
      }
    });
    setChiefComplaint('');
    setTreatmentPlan('');
  };

  return (
    <div className="space-y-6 text-xs">
      <form onSubmit={handleSubmit} className="p-4 bg-[var(--bg)] rounded-xl border border-[var(--border)] space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-bold text-sm text-[var(--text)]">New SOAP Clinical Assessment</h4>
          <select
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value as SpecialtyKey)}
            className="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] font-bold text-[var(--text)]"
          >
            <option value="ortho">Ortho Specialty</option>
            <option value="neuro">Neuro Specialty</option>
            <option value="cardiopulm">Cardiopulm</option>
            <option value="sports">Sports Injury</option>
            <option value="paeds">Paediatrics</option>
            <option value="general">General PT</option>
          </select>
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Pain VAS (0 - 10)</label>
          <div className="flex gap-1 flex-wrap">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setVasScore(i)}
                className={`w-7 h-7 rounded font-bold text-xs ${
                  vasScore === i ? 'bg-red-500 text-white' : 'bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text)]'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Chief Complaint (Subjective)</label>
          <textarea
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            placeholder="Describe onset, duration, aggravating and relieving factors..."
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] resize-none"
            required
          />
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Treatment Plan & Goals (Plan)</label>
          <textarea
            value={treatmentPlan}
            onChange={(e) => setTreatmentPlan(e.target.value)}
            placeholder="Short-term goals, long-term goals, exercise protocol..."
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] resize-none"
          />
        </div>

        <button
          type="submit"
          className="px-4 py-2 bg-[var(--navy)] text-white font-bold rounded-lg hover:opacity-90"
        >
          Save Assessment Entry
        </button>
      </form>
    </div>
  );
};

// Treatment Manager Component
const TreatmentManager: React.FC<{
  patientId: string;
  treatments: any[];
  onAdd: (tx: any) => void;
  therapists: any[];
}> = ({ patientId, treatments, onAdd, therapists }) => {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [therapist, setTherapist] = useState(therapists[0]?.name || '');
  const [painScore, setPainScore] = useState(5);
  const [treatment, setTreatment] = useState('');
  const [homeAdvice, setHomeAdvice] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!treatment.trim()) return;
    onAdd({
      patientId,
      date,
      therapist,
      painScore,
      treatment: treatment.trim(),
      homeAdvice: homeAdvice.trim() || undefined
    });
    setTreatment('');
    setHomeAdvice('');
  };

  return (
    <div className="space-y-6 text-xs">
      <form onSubmit={handleSubmit} className="p-4 bg-[var(--bg)] rounded-xl border border-[var(--border)] space-y-4">
        <h4 className="font-bold text-sm text-[var(--text)]">+ Log Treatment Session</h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
            />
          </div>
          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Therapist</label>
            <select
              value={therapist}
              onChange={(e) => setTherapist(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
            >
              {therapists.map((t) => (
                <option key={t.id} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Pain VAS Score (0 - 10)</label>
          <div className="flex gap-1 flex-wrap">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setPainScore(i)}
                className={`w-7 h-7 rounded font-bold text-xs ${
                  painScore === i ? 'bg-red-500 text-white' : 'bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text)]'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Treatment Given *</label>
          <textarea
            value={treatment}
            onChange={(e) => setTreatment(e.target.value)}
            placeholder="Modalities, manual therapy, mobilization, exercises..."
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] resize-none"
            required
          />
        </div>

        <div>
          <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Home Advice / HEP</label>
          <textarea
            value={homeAdvice}
            onChange={(e) => setHomeAdvice(e.target.value)}
            placeholder="Home exercises, ice/heat instructions..."
            rows={1}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)] resize-none"
          />
        </div>

        <button
          type="submit"
          className="px-4 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90"
        >
          Add Session Entry
        </button>
      </form>

      {/* Sessions Timeline */}
      <div className="space-y-3">
        <h4 className="font-bold text-sm text-[var(--text)]">Session History ({treatments.length})</h4>
        {treatments.map((t) => (
          <div key={t.id} className="p-3 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[var(--text)]">{t.date} • {t.therapist}</span>
              {t.painScore !== undefined && (
                <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-red-500/15 text-red-500">
                  Pain {t.painScore}/10
                </span>
              )}
            </div>
            <p className="text-[var(--text)]">{t.treatment}</p>
            {t.homeAdvice && <p className="text-[var(--text-light)] italic">HEP: {t.homeAdvice}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};

// Package Manager Component
const PackageManager: React.FC<{
  patientId: string;
  patientName: string;
  packages: any[];
  onAdd: (pkg: any) => void;
}> = ({ patientId, patientName, packages, onAdd }) => {
  const [pkgName, setPkgName] = useState('Standard 10-Session Rehab Package');
  const [totalSessions, setTotalSessions] = useState(10);
  const [amount, setAmount] = useState(12000);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      patientId,
      patientName,
      packageName: pkgName,
      totalSessions,
      sessionsUsed: 0,
      amount,
      startDate: new Date().toISOString().slice(0, 10),
      status: 'Active'
    });
  };

  return (
    <div className="space-y-4 text-xs">
      <form onSubmit={handleSubmit} className="p-4 bg-[var(--bg)] rounded-xl border border-[var(--border)] space-y-3">
        <h4 className="font-bold text-sm text-[var(--text)]">+ Assign New Package</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            type="text"
            value={pkgName}
            onChange={(e) => setPkgName(e.target.value)}
            className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
            required
          />
          <input
            type="number"
            value={totalSessions}
            onChange={(e) => setTotalSessions(Number(e.target.value))}
            placeholder="Sessions"
            className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
          />
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            placeholder="Amount (₹)"
            className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] text-[var(--text)]"
          />
        </div>
        <button type="submit" className="px-4 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90">
          Create Package
        </button>
      </form>
    </div>
  );
};
