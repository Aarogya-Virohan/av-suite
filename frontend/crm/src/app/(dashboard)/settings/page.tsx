'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { AuditLog, User } from '../../../types/api';
import { useUsers } from '../../../features/users/api';
import { useAuditLogs } from '../../../features/audit/api';
import { Settings as SettingsIcon, Users, FileText, AlertCircle, Save, Plus, Palette, Upload } from 'lucide-react';
import { toast } from 'sonner';

type TabKey = 'clinic' | 'users' | 'audit';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('clinic');
  const [clinicName, setClinicName] = useState('Aarogya Virohan Health Center');
  const [phone, setPhone] = useState('+919876543210');
  const [email, setEmail] = useState('contact@aarogya.com');
  const [address, setAddress] = useState('Sector 14, Main Road, New Delhi');
  const [brandColor, setBrandColor] = useState('#0b2c5f');
  const [doctorName, setDoctorName] = useState('Dr. Ananya Roy');
  const [regNo, setRegNo] = useState('REG-2026-PT88');
  const [logoBase64, setLogoBase64] = useState<string | null>(null);

  const { data: usersResponse, isLoading: isLoadingUsers } = useUsers();
  const users = usersResponse || [];

  const { data: auditResponse, isLoading: isLoadingAudit } = useAuditLogs(1, 50);
  const auditLogs = auditResponse?.data || [];

  const handleBrandColorChange = (color: string) => {
    setBrandColor(color);
    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty('--brand-navy', color);
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 200 * 1024) {
      toast.error('Logo file size must be under 200KB');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setLogoBase64(reader.result as string);
      toast.success('Logo uploaded & preview updated');
    };
    reader.readAsDataURL(file);
  };

  const handleSaveClinic = (e: React.FormEvent) => {
    e.preventDefault();
    if (typeof window !== 'undefined') {
      localStorage.setItem('av_crm_brand_color', brandColor);
      if (logoBase64) localStorage.setItem('av_crm_logo', logoBase64);
    }
    toast.success('Clinic branding & settings saved successfully!');
  };

  const auditColumns: Column<AuditLog>[] = [
    { key: 'action', header: 'Action', render: (log) => <span className="font-mono text-xs text-teal-600 font-bold">{log.action}</span> },
    { key: 'entity_type', header: 'Entity Type' },
    { key: 'entity_id', header: 'Entity ID', render: (log) => log.entity_id || '-' },
    { key: 'user_id', header: 'User ID', render: (log) => log.user_id || 'System' },
    { key: 'details', header: 'Details', render: (log) => JSON.stringify(log.details) },
    { key: 'created_at', header: 'Timestamp', render: (log) => new Date(log.created_at).toLocaleString() },
  ];

  const userColumns: Column<User>[] = [
    { key: 'name', header: 'User Name', render: (u) => `${u.first_name} ${u.last_name}` },
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role', render: (u) => <span className="uppercase text-xs font-bold text-teal-600">{u.role}</span> },
    { key: 'is_active', header: 'Status', render: (u) => (u.is_active ? 'Active' : 'Inactive') },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Clinic Settings</h1>
          <p className="text-sm text-slate-500">Manage clinic preferences, branding, users & audit logs</p>
        </div>

        {/* Tab Selection */}
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setActiveTab('clinic')}
            className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${
              activeTab === 'clinic'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <SettingsIcon className="w-4 h-4" />
            <span>Clinic Settings & Branding</span>
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${
              activeTab === 'users'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>User Management</span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${
              activeTab === 'audit'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Audit Log ({auditLogs.length})</span>
          </button>
        </div>

        {/* Clinic Branding Settings Tab */}
        {activeTab === 'clinic' && (
          <form onSubmit={handleSaveClinic} className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-6 max-w-2xl">
            <div className="p-3 bg-teal-50 dark:bg-teal-950 border border-teal-200 dark:border-teal-800 rounded-lg text-xs text-teal-800 dark:text-teal-200">
              ✨ These branding settings automatically apply to invoices, receipts, prescriptions, and public booking forms.
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Clinic Name</label>
                <input
                  type="text"
                  value={clinicName}
                  onChange={(e) => setClinicName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Clinic Phone</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Brand Accent Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={brandColor}
                      onChange={(e) => handleBrandColorChange(e.target.value)}
                      className="w-10 h-9 p-0.5 rounded cursor-pointer border"
                    />
                    <span className="text-xs font-mono text-slate-500 uppercase">{brandColor}</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Clinic Address</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Lead Doctor / Therapist Name</label>
                  <input
                    type="text"
                    value={doctorName}
                    onChange={(e) => setDoctorName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Medical Registration No.</label>
                  <input
                    type="text"
                    value={regNo}
                    onChange={(e) => setRegNo(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Clinic Logo Upload */}
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Clinic Logo (For Invoices, Prescriptions & Booking Form, Max 200KB)
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleLogoUpload}
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100"
                />
                {logoBase64 && (
                  <div className="mt-3 p-2 bg-slate-50 dark:bg-slate-950 rounded-lg border w-fit">
                    <img src={logoBase64} alt="Clinic Logo Preview" className="h-12 object-contain rounded" />
                  </div>
                )}
              </div>
            </div>

            <button
              type="submit"
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Save className="w-4 h-4" />
              <span>Save Branding Settings</span>
            </button>
          </form>
        )}

        {/* User Management Tab (Blocked Stub State) */}
        {activeTab === 'users' && (
          <div className="space-y-4">
            <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-amber-800 dark:text-amber-200 font-semibold">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
                <span>Blocked Feature — `/users` CRUD endpoints unconfirmed on backend (Q4). Submitting will no-op.</span>
              </div>
              <button
                onClick={() => toast.error('User management endpoint not yet available')}
                className="px-3 py-1.5 bg-amber-600 text-white text-xs font-bold rounded-lg flex items-center gap-1 opacity-75 cursor-not-allowed"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add User (Stub)</span>
              </button>
            </div>

            <DataTable columns={userColumns} data={users} isLoading={isLoadingUsers} />
          </div>
        )}

        {/* Audit Log Tab */}
        {activeTab === 'audit' && (
          <DataTable
            columns={auditColumns}
            data={auditLogs}
            isLoading={isLoadingAudit}
            searchField={(log) => `${log.action} ${log.entity_type}`}
            searchPlaceholder="Search audit logs by action or entity type..."
          />
        )}
      </div>
    </AppShell>
  );
}
