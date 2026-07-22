'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Patient, PatientStatus } from '@/types/crm';

interface PatientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (patientData: any) => void;
  patient?: Patient | null;
}

export const PatientModal: React.FC<PatientModalProps> = ({
  isOpen,
  onClose,
  onSave,
  patient
}) => {
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [age, setAge] = useState<number | ''>('');
  const [gender, setGender] = useState<'Male' | 'Female' | 'Other'>('Male');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [referralSource, setReferralSource] = useState('');
  const [status, setStatus] = useState<PatientStatus>('Active');
  const [diagnosis, setDiagnosis] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');

  useEffect(() => {
    if (patient) {
      setName(patient.name || '');
      setMobile(patient.mobile || '');
      setAge(patient.age || '');
      setGender(patient.gender || 'Male');
      setEmail(patient.email || '');
      setAddress(patient.address || '');
      setReferralSource(patient.referralSource || '');
      setStatus(patient.status || 'Active');
      setDiagnosis(patient.diagnosis || '');
      setMedicalHistory(patient.medicalHistory || '');
    } else {
      setName('');
      setMobile('');
      setAge('');
      setGender('Male');
      setEmail('');
      setAddress('');
      setReferralSource('');
      setStatus('Active');
      setDiagnosis('');
      setMedicalHistory('');
    }
  }, [patient, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !mobile.trim()) {
      alert('Patient Name and Mobile number are required.');
      return;
    }
    onSave({
      name: name.trim(),
      mobile: mobile.trim(),
      age: age === '' ? undefined : Number(age),
      gender,
      email: email.trim() || undefined,
      address: address.trim() || undefined,
      referralSource: referralSource.trim() || undefined,
      status,
      diagnosis: diagnosis.trim() || undefined,
      medicalHistory: medicalHistory.trim() || undefined
    });
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card max-w-xl p-6 space-y-5 my-8">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <h2 className="text-lg font-bold text-[var(--text)]">
            {patient ? 'Edit Patient Profile' : 'Add New Patient Intake'}
          </h2>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
                Full Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Rajesh Malhotra"
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
                Mobile Number *
              </label>
              <input
                type="tel"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="e.g. 9820112233"
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
                Age
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="45"
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
                Gender
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value as any)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
                Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as PatientStatus)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
              >
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="Discharged">Discharged</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="patient@example.com"
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
              Address
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="House/Flat No, Area, City"
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
              Referral Source
            </label>
            <input
              type="text"
              value={referralSource}
              onChange={(e) => setReferralSource(e.target.value)}
              placeholder="e.g. Doctor Referral, Google, Instagram"
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
              Primary Diagnosis / Chief Complaint
            </label>
            <input
              type="text"
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              placeholder="e.g. Chronic Lower Back Pain (L4-L5 Disc Herniation)"
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[var(--text-light)] uppercase mb-1">
              Medical History / Notes
            </label>
            <textarea
              value={medicalHistory}
              onChange={(e) => setMedicalHistory(e.target.value)}
              placeholder="Comorbidities, past surgeries, active medications..."
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--teal)] resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold rounded-lg border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 text-sm font-bold rounded-lg bg-[var(--navy)] text-white hover:opacity-90 shadow-sm"
            >
              {patient ? 'Save Changes' : 'Create Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
