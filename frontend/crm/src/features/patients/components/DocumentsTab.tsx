'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { patientDocumentFormSchema, PatientDocumentFormValues } from '../../../lib/schemas';
import { SlideOver } from '../../../components/ui/SlideOver';
import { FileText, Download, Plus, Loader2 } from 'lucide-react';
import { Button, Card, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';
import { API_BASE_URL } from '../../../lib/api-client';
import { getStoredToken } from '../../../lib/auth';

import { usePatientDocuments, useUploadPatientDocument } from '../api';

const CATEGORIES: { value: PatientDocumentFormValues['category']; label: string }[] = [
  { value: 'medical_report', label: 'Medical Report' },
  { value: 'prescription', label: 'Prescription' },
  { value: 'lab_result', label: 'Lab Result' },
  { value: 'x_ray_scan', label: 'X-ray / Scan' },
  { value: 'consent_form', label: 'Consent Form' },
  { value: 'id_proof', label: 'ID Proof' },
  { value: 'other', label: 'Other' },
];
const categoryLabel = (v: string) => CATEGORIES.find((c) => c.value === v)?.label ?? v.replace(/_/g, ' ');
const docDate = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

export function DocumentsTab({ patientId }: { patientId: string }) {
  const { data: response, isLoading } = usePatientDocuments(patientId);
  const documents = response?.items || [];
  const [isSlideOpen, setIsSlideOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PatientDocumentFormValues>({
    resolver: zodResolver(patientDocumentFormSchema),
    defaultValues: {
      patient_id: patientId,
      label: '',
      category: 'medical_report',
      notes: '',
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }

    // Client-side validation: max 10MB
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size exceeds maximum limit of 10MB');
      e.target.value = '';
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const uploadDocument = useUploadPatientDocument();

  const openUpload = () => {
    reset({ patient_id: patientId, label: '', category: 'medical_report', notes: '' });
    setSelectedFile(null);
    setIsSlideOpen(true);
  };

  const onSubmit = (values: PatientDocumentFormValues) => {
    if (uploadDocument.isPending) return;
    if (!selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }

    const formData = new FormData();
    formData.append('label', values.label.trim());
    formData.append('category', values.category);
    if (values.notes) formData.append('notes', values.notes);
    if (values.treatment_id) formData.append('treatment_id', values.treatment_id);
    formData.append('file', selectedFile);

    uploadDocument.mutate(
      {
        patientId,
        payload: formData,
      },
      {
        onSuccess: () => {
          toast.success('Document record saved successfully.');
          reset();
          setSelectedFile(null);
          setIsSlideOpen(false);
        },
        onError: (err: any) => {
          toast.error(err?.message || 'Failed to save document.');
        },
      }
    );
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display text-base font-bold text-ink">Patient Documents</h3>
          <p className="text-xs text-muted">Medical reports, scans, prescriptions and consent forms</p>
        </div>
        <Button onClick={openUpload}>
          <Plus className="h-4 w-4" />
          <span>Upload Document</span>
        </Button>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 p-8 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin text-grove" /> Loading documents...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted">No documents uploaded for this patient.</div>
        ) : (
          <div className="divide-y divide-line-soft">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between gap-3 p-4 transition-colors hover:bg-canvas/70">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[10px] bg-logo-teal-wash text-logo-teal-ink">
                    <FileText className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">{doc.label}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-ink-2">{categoryLabel(doc.category)}</span>
                      <span>{formatFileSize(doc.file_size)}</span>
                      <span aria-hidden="true">·</span>
                      <span>{docDate.format(new Date(doc.created_at))}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={async () => {
                    try {
                      const downloadUrl = `${API_BASE_URL}/documents/${doc.id}/download`;
                      const token = getStoredToken();
                      const res = await fetch(downloadUrl, {
                        headers: {
                          'Authorization': `Bearer ${token}`
                        }
                      });
                      if (!res.ok) throw new Error('Download failed');
                      const blob = await res.blob();
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = doc.label;
                      document.body.appendChild(a);
                      a.click();
                      window.URL.revokeObjectURL(url);
                      a.remove();
                    } catch (err) {
                      toast.error('Failed to download document');
                    }
                  }}
                  title="Download File"
                  aria-label={`Download ${doc.label}`}
                  className="grid h-9 w-9 shrink-0 cursor-pointer place-items-center rounded-lg text-muted transition-colors hover:bg-grove-wash hover:text-grove"
                >
                  <Download className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Upload SlideOver */}
      <SlideOver
        isOpen={isSlideOpen}
        onClose={() => setIsSlideOpen(false)}
        title="Upload Patient Document"
        subtitle="Attach MRI scans, prescriptions or lab reports"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div>
            <FieldLabel htmlFor="doc-label">Document Label *</FieldLabel>
            <input id="doc-label" {...register('label')} type="text" placeholder="e.g. Lumbar Spine MRI Report" className={cn(inputClass, errors.label && 'border-danger')} />
            {errors.label && <p className="mt-1.5 text-xs font-medium text-danger">{errors.label.message}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="doc-category">Category *</FieldLabel>
            <select id="doc-category" {...register('category')} className={inputClass}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <FieldLabel htmlFor="doc-file">File (PDF or image, max 10MB) *</FieldLabel>
            <input
              id="doc-file"
              type="file"
              onChange={handleFileChange}
              accept="image/*,application/pdf"
              className="w-full cursor-pointer text-xs text-muted file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-grove-wash file:px-4 file:py-2 file:text-xs file:font-semibold file:text-grove hover:file:bg-[#d3eedc]"
            />
            {selectedFile && <p className="mt-1.5 text-xs text-muted">{selectedFile.name} · {formatFileSize(selectedFile.size)}</p>}
          </div>

          <div>
            <FieldLabel htmlFor="doc-notes">Notes</FieldLabel>
            <textarea id="doc-notes" {...register('notes')} rows={2} placeholder="Additional comments..." className={cn(inputClass, 'h-auto py-2')} />
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
            <Button type="button" variant="ghost" onClick={() => setIsSlideOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={uploadDocument.isPending}>
              {uploadDocument.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{uploadDocument.isPending ? 'Uploading...' : 'Upload Document'}</span>
            </Button>
          </div>
        </form>
      </SlideOver>
    </div>
  );
}
