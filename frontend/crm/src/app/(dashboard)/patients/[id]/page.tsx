'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppShell } from '../../../../components/layout/AppShell';
import { usePatient, useDeletePatient } from '../../../../features/patients/api';
import { useAuthStore } from '../../../../store';
import { getPermissionsForRole, canAccessModule, usePermissionSubscription } from '../../../../config/permissions';
import { AccessRestricted } from '../../../../components/ui/AccessRestricted';
import { TreatmentsTab } from '../../../../features/patients/components/TreatmentsTab';
import { SoapNotesTab } from '../../../../features/patients/components/SoapNotesTab';
import { DocumentsTab } from '../../../../features/patients/components/DocumentsTab';
import { ProgressionTab } from '../../../../features/patients/components/ProgressionTab';
import { PatientBillingTab } from '../../../../features/patients/components/PatientBillingTab';
import { EditPatientSlideOver } from '../../../../features/patients/components/EditPatientSlideOver';
import { WhatsAppButton } from '../../../../components/ui/WhatsAppButton';
import { ArrowLeft, FileText, CreditCard, Clock, Stethoscope, MessageSquare, Activity, FileCheck, Camera, Dumbbell, Edit2, Trash2 } from 'lucide-react';
import { API_BASE_URL } from '../../../../lib/api-client';
import { getStoredToken } from '../../../../lib/auth';
import { toast } from 'sonner';
import { usePrescriptions, useCreatePrescription, useGeneratePrescriptionPdf } from '../../../../features/prescriptions/api';
import { Avatar, Button, Card } from '../../../../components/ui/brand';
import { cn } from '../../../../lib/cn';

type TabKey = 'timeline' | 'documents' | 'treatments' | 'soapNotes' | 'assessments' | 'progression' | 'rx' | 'billing';

export default function PatientWorkspacePage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const params = useParams();
  const router = useRouter();
  const patientId = params?.id as string;
  const role = useAuthStore((s) => s.role);

  const { data: patient, isLoading } = usePatient(patientId);
  const [activeTab, setActiveTab] = useState<TabKey>('timeline');
  const [isEditOpen, setIsEditOpen] = useState(false);
  const deletePatient = useDeletePatient();

  const { data: prescriptions, isLoading: isRxLoading } = usePrescriptions(patientId);
  const createRx = useCreatePrescription();
  const generatePdf = useGeneratePrescriptionPdf();

  const permissions = getPermissionsForRole(role).patientTabs;

  if (!canAccessModule('patients')) {
    return (
      <AppShell>
        <AccessRestricted message="Patient workspace access is restricted for your role." />
      </AppShell>
    );
  }

  if (isLoading) {
    return (
      <AppShell>
        <Card className="p-10 text-center text-sm text-muted">Loading patient workspace...</Card>
      </AppShell>
    );
  }

  if (!patient) {
    return (
      <AppShell>
        <Card className="space-y-4 p-10 text-center">
          <p className="font-medium text-muted">Patient not found</p>
          <Button onClick={() => router.push('/patients')}>Return to Patients Directory</Button>
        </Card>
      </AppShell>
    );
  }

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${patient.first_name} ${patient.last_name}?`)) {
      try {
        await deletePatient.mutateAsync(patient.id);
        toast.success('Patient deleted successfully');
        router.push('/patients');
      } catch (err) {
        toast.error('Failed to delete patient');
      }
    }
  };

  const handleGenerateRx = async () => {
    try {
      let rxId: string;
      if (prescriptions && prescriptions.length > 0) {
        rxId = prescriptions[0].id;
      } else {
        const newRx = await createRx.mutateAsync({
          patient_id: patientId,
          physio_notes: "Auto-generated prescription.",
          items: [],
        });
        rxId = newRx.id;
      }

      await generatePdf.mutateAsync(rxId);
      toast.success('Prescription generated successfully! Downloading...');

      const downloadUrl = `${API_BASE_URL}/prescriptions/${rxId}/pdf/download`;
      
      const token = getStoredToken();
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Prescription-${patient.first_name}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      toast.error('Failed to generate or download Prescription PDF');
    }
  };

  const allTabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
    { key: 'timeline', label: 'Timeline', icon: Clock },
    { key: 'documents', label: 'Documents', icon: FileText },
    { key: 'treatments', label: 'Treatments', icon: Stethoscope },
    { key: 'soapNotes', label: 'SOAP Notes', icon: FileText },
    { key: 'assessments', label: 'Assessments', icon: Stethoscope },
    { key: 'progression', label: 'Progression', icon: Activity },
    { key: 'rx', label: 'Rx Prescription', icon: FileCheck },
    { key: 'billing', label: 'Billing', icon: CreditCard },
  ];

  const visibleTabs = allTabs.filter((t) => {
    if (t.key === 'progression' || t.key === 'rx') return permissions.treatments;
    return permissions[t.key as keyof typeof permissions];
  });

  const ACTION_CLASS =
    'inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-[10px] border border-line bg-card px-3 text-xs font-semibold text-ink-2 transition-colors hover:border-slate-300 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50';

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Back Link */}
        <button
          onClick={() => router.push('/patients')}
          className="flex cursor-pointer items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-grove"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Patients Directory</span>
        </button>

        {/* Sticky Patient Workspace Header */}
        <Card className="sticky top-0 z-10 space-y-4 p-6">
          <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-start">
            <div className="flex items-center gap-4">
              <Avatar
                name={`${patient.first_name} ${patient.last_name}`}
                size={60}
                className="ring-4 ring-logo-teal-wash"
              />
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="font-display text-2xl font-bold tracking-tight text-ink">
                    {patient.first_name} {patient.last_name}
                  </h1>
                  <WhatsAppButton phone={patient.phone} name={`${patient.first_name} ${patient.last_name}`} />
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                  <span>
                    Phone: <strong className="font-semibold text-ink-2">{patient.phone}</strong>
                  </span>
                  <span aria-hidden="true">·</span>
                  <span>
                    Gender: <strong className="font-semibold capitalize text-ink-2">{patient.gender || 'Not set'}</strong>
                  </span>
                  {patient.date_of_birth && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>
                        DOB: <strong className="font-semibold text-ink-2">{patient.date_of_birth}</strong>
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Record actions */}
            {(getPermissionsForRole(role).actions.createEditPatient || getPermissionsForRole(role).actions.deletePatient) && (
              <div className="flex items-center gap-2">
                {getPermissionsForRole(role).actions.createEditPatient && (
                  <button onClick={() => setIsEditOpen(true)} className={ACTION_CLASS}>
                    <Edit2 className="h-3.5 w-3.5" />
                    <span>Edit</span>
                  </button>
                )}

                {getPermissionsForRole(role).actions.deletePatient && (
                  <button
                    onClick={handleDelete}
                    disabled={deletePatient.isPending}
                    className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-[10px] bg-danger-wash px-3 text-xs font-semibold text-danger transition-colors hover:bg-[#f7d6d1] disabled:opacity-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Delete</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Clinical tools */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Disabled until the report is built from the patient's real finalized
                session (backend clinical summary). It used to send hardcoded pain
                scores and treatment text to every patient. */}
            <button
              disabled
              title="Coming soon: the report will be built from the latest finalized session"
              className={ACTION_CLASS}
            >
              <MessageSquare className="h-3.5 w-3.5 text-fresh" />
              <span>WA Session Report</span>
            </button>

            <a
              href={`${(process.env.NEXT_PUBLIC_POSTURE_APP_URL || 'http://localhost:3002').replace(/\/+$/, '')}/analyze?patient_id=${patient.id}`}
              target="_blank"
              rel="noreferrer"
              className={ACTION_CLASS}
            >
              <Camera className="h-3.5 w-3.5 text-logo-teal" />
              <span>AI Posture Analysis</span>
            </a>

            <a
              href={`${(process.env.NEXT_PUBLIC_EXERCISE_APP_URL || 'http://localhost:3001').replace(/\/+$/, '')}/prescribe?patient_id=${patient.id}`}
              target="_blank"
              rel="noreferrer"
              className={ACTION_CLASS}
            >
              <Dumbbell className="h-3.5 w-3.5 text-info" />
              <span>Exercise Library</span>
            </a>

            <Button
              onClick={handleGenerateRx}
              disabled={isRxLoading || createRx.isPending || generatePdf.isPending}
              className="h-9 px-3 text-xs"
            >
              <FileCheck className="h-3.5 w-3.5" />
              <span>Auto-Rx</span>
            </Button>
          </div>

          {/* Chief Complaint Banner */}
          <div className="rounded-xl border border-line bg-canvas px-4 py-3 text-[13px]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-logo-teal-ink">Chief Complaint: </span>
            <span className="text-ink-2">{patient.chief_complaint}</span>
          </div>

          {/* Tab Navigation */}
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pt-1">
            {visibleTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 whitespace-nowrap rounded-[9px] px-3.5 py-2 text-[13px] font-semibold transition-colors',
                    isActive ? 'bg-grove-wash text-grove' : 'text-muted hover:bg-slate-100 hover:text-ink',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </Card>

        {/* Tab Content Body */}
        <div>
          {activeTab === 'timeline' && (
            <Card className="space-y-4 p-6">
              <h3 className="font-display text-base font-bold text-ink">Patient Activity Timeline</h3>
              <div className="flex items-start gap-3">
                <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-logo-teal ring-4 ring-logo-teal-wash" aria-hidden="true" />
                <p className="text-[13px] text-ink-2">
                  Patient record created on{' '}
                  <strong className="font-semibold text-ink">{new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(patient.created_at))}</strong>.
                </p>
              </div>
            </Card>
          )}

          {activeTab === 'documents' && <DocumentsTab patientId={patient.id} />}

          {activeTab === 'treatments' && <TreatmentsTab patientId={patient.id} />}

          {activeTab === 'soapNotes' && <SoapNotesTab patientId={patient.id} isReassessmentOnly={false} />}

          {activeTab === 'assessments' && <SoapNotesTab patientId={patient.id} isReassessmentOnly={true} />}

          {activeTab === 'progression' && <ProgressionTab patientId={patient.id} patientName={`${patient.first_name} ${patient.last_name}`} />}

          {activeTab === 'rx' && (
            <Card className="space-y-4 p-8 text-center">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-grove-wash text-grove">
                <FileCheck className="h-6 w-6" />
              </span>
              <h3 className="font-display text-base font-bold text-ink">Prescription (Rx) Generator</h3>
              <p className="mx-auto max-w-md text-xs text-muted">
                Generates a branded PDF prescription containing clinic logo, diagnosis history, and exercise routine.
              </p>
              <Button
                onClick={handleGenerateRx}
                disabled={generatePdf.isPending || createRx.isPending || isRxLoading}
                className="mx-auto"
              >
                <FileCheck className="h-4 w-4" />
                <span>{generatePdf.isPending ? 'Generating...' : 'Generate Prescription PDF'}</span>
              </Button>
            </Card>
          )}

          {activeTab === 'billing' && <PatientBillingTab patientId={patient.id} />}
        </div>
      </div>
      <EditPatientSlideOver isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} patient={patient} />
    </AppShell>
  );
}
