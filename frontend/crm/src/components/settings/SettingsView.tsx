'use client';

import React, { useState } from 'react';
import { Save, Check, RefreshCw, Upload, Shield } from 'lucide-react';
import { useCRMStore } from '@/lib/store';

export const SettingsView: React.FC = () => {
  const { branding, updateBranding, auditLogs } = useCRMStore();

  const [clinicName, setClinicName] = useState(branding.clinicName);
  const [phone, setPhone] = useState(branding.phone);
  const [address, setAddress] = useState(branding.address);
  const [doctorName, setDoctorName] = useState(branding.doctorName);
  const [regNo, setRegNo] = useState(branding.regNo);
  const [brandColor, setBrandColor] = useState(branding.brandColor || '#0B2C5F');
  const [logoBase64, setLogoBase64] = useState(branding.logoBase64 || '');
  const [apiUrl, setApiUrl] = useState(branding.apiUrl || '');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleColorChange = (color: string) => {
    setBrandColor(color);
    document.documentElement.style.setProperty('--brand', color);
    document.documentElement.style.setProperty('--sidebar-bg', color);
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 200 * 1024) {
        alert('Logo image must be under 200KB.');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        setLogoBase64(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateBranding({
      clinicName: clinicName.trim(),
      phone: phone.trim(),
      address: address.trim(),
      doctorName: doctorName.trim(),
      regNo: regNo.trim(),
      brandColor,
      logoBase64,
      apiUrl: apiUrl.trim()
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Backend API Connection Banner */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] p-5 rounded-xl shadow-sm space-y-3 text-xs">
        <h3 className="font-bold text-sm text-[var(--text)] flex items-center gap-2">
          <Shield className="w-4 h-4 text-[var(--teal)]" />
          Backend Connection & API Configuration
        </h3>
        <p className="text-[var(--text-light)]">
          The CRM is connected to the shared FastAPI + PostgreSQL backend. Enter an API URL if connecting to a remote environment.
        </p>

        <div className="flex gap-2 max-w-lg">
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000 (Leave blank for local mock state)"
            className="flex-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)]"
          />
          <button
            type="button"
            onClick={async () => {
              try {
                const base = apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const origin = new URL(base).origin;
                const response = await fetch(`${origin}/health`);
                if (response.ok) {
                  const data = await response.json();
                  if (data.status === 'healthy') {
                    alert('FastAPI Connection test: Healthy ✓');
                  } else {
                    alert('FastAPI Connection test: Unhealthy ⚠️');
                  }
                } else {
                  alert('FastAPI Connection test: Failed ❌');
                }
              } catch (error) {
                alert('FastAPI Connection test: Failed ❌');
              }
            }}
            className="px-4 py-2 bg-[var(--teal)] text-white font-bold rounded-lg hover:opacity-90 inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Test API
          </button>
        </div>
      </div>

      {/* Clinic Branding Form */}
      <form onSubmit={handleSubmit} className="bg-[var(--card-bg)] border border-[var(--border)] p-6 rounded-xl shadow-sm space-y-5 text-xs">
        <h3 className="font-bold text-base text-[var(--text)] border-b border-[var(--border)] pb-3">
          Clinic Branding & Document Settings
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Clinic Name</label>
            <input
              type="text"
              value={clinicName}
              onChange={(e) => setClinicName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm font-semibold"
              required
            />
          </div>

          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Phone Number</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm"
              required
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Address</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm"
            />
          </div>

          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Lead Doctor / Head Therapist Name</label>
            <input
              type="text"
              value={doctorName}
              onChange={(e) => setDoctorName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm"
            />
          </div>

          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Registration Number</label>
            <input
              type="text"
              value={regNo}
              onChange={(e) => setRegNo(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] text-sm"
            />
          </div>

          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Primary Brand Color</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={brandColor}
                onChange={(e) => handleColorChange(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer border border-[var(--border)] p-1 bg-[var(--bg)]"
              />
              <span className="font-mono font-bold text-sm text-[var(--text)]">{brandColor}</span>
            </div>
          </div>

          <div>
            <label className="block font-bold text-[var(--text-light)] uppercase mb-1">Clinic Logo (PNG/JPG under 200KB)</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleLogoUpload}
              className="w-full px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)]"
            />
            {logoBase64 && (
              <img src={logoBase64} alt="Clinic Logo Preview" className="h-10 mt-2 rounded border border-[var(--border)] object-cover" />
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 pt-3 border-t border-[var(--border)]">
          <button
            type="submit"
            className="px-6 py-2.5 bg-[var(--navy)] text-white font-bold text-xs rounded-xl hover:opacity-90 transition-opacity inline-flex items-center gap-2 shadow-sm"
          >
            <Save className="w-4 h-4" />
            Save Branding Configuration
          </button>
          {savedSuccess && (
            <span className="text-emerald-600 font-bold flex items-center gap-1 animate-pulse">
              <Check className="w-4 h-4" />
              Settings saved successfully!
            </span>
          )}
        </div>
      </form>

      {/* Audit Log Viewer */}
      <div className="bg-[var(--card-bg)] border border-[var(--border)] p-6 rounded-xl shadow-sm space-y-4 text-xs">
        <h3 className="font-bold text-base text-[var(--text)] border-b border-[var(--border)] pb-3">
          System Audit Trail & Security Logs
        </h3>

        <div className="space-y-2 max-h-60 overflow-y-auto">
          {auditLogs.map((log) => (
            <div key={log.id} className="p-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg)] flex items-center justify-between">
              <div>
                <p className="font-bold text-[var(--text)]">{log.description}</p>
                <p className="text-[10px] text-[var(--text-light)] uppercase tracking-wider">{log.action} • {log.entityType}</p>
              </div>
              <span className="text-[10px] text-[var(--text-light)] font-mono">{new Date(log.createdAt).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
