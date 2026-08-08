'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useAuthStore } from '../../../store';
import { canAccessModule } from '../../../config/permissions';
import { useUsers } from '../../../features/users/api';
import { User, UserRole } from '../../../types/api';
import { ShieldAlert, AlertCircle, Plus, Edit, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

export default function TherapistsPage() {
  const role = useAuthStore((s) => s.role) || ('admin' as UserRole);
  const { data: usersResponse, isLoading } = useUsers();
  const users = usersResponse || [];
  const initialTherapists = users.filter((u: User) => u.role === 'therapist' || u.role === 'admin');
  const [therapists, setTherapists] = useState<User[]>([]);

  React.useEffect(() => {
    setTherapists(initialTherapists);
  }, [usersResponse]);
  const [isSlideOpen, setIsSlideOpen] = useState(false);

  // Form fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');

  const handleCreateTherapist = (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName || !lastName || !email) {
      toast.error('First Name, Last Name, and Email are required');
      return;
    }

    const newTherapist: User = {
      id: `usr_therapist_${Date.now()}`,
      clinic_id: 'cln_aarogya_1',
      email,
      role: 'therapist',
      first_name: firstName,
      last_name: lastName,
      phone: phone || '+91 9876543210',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setTherapists([...therapists, newTherapist]);
    toast.success(`Therapist ${firstName} ${lastName} created successfully! (Stubbed data layer)`);
    setIsSlideOpen(false);
    setFirstName('');
    setLastName('');
    setEmail('');
    setPhone('');
  };

  if (!canAccessModule(role, 'therapists')) {
    return (
      <AppShell>
        <div className="p-8 max-w-md mx-auto text-center space-y-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          <ShieldAlert className="w-12 h-12 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Access Restricted</h2>
          <p className="text-xs text-slate-500">Therapists directory and payroll is restricted to Administrators only.</p>
        </div>
      </AppShell>
    );
  }

  const columns: Column<User>[] = [
    { key: 'name', header: 'Therapist Name', render: (u) => <span className="font-bold">{u.first_name} {u.last_name}</span> },
    { key: 'email', header: 'Email' },
    { key: 'phone', header: 'Phone' },
    { key: 'payroll', header: 'Monthly Salary', render: () => <span className="text-rose-600 font-bold">₹35,000 / mo</span> },
    { key: 'status', header: 'Status', render: (u) => (u.is_active ? <span className="text-emerald-600 font-bold text-xs">Active</span> : 'Inactive') },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Therapists Directory & Payroll</h1>
            <p className="text-sm text-slate-500">Manage clinic therapists & monthly compensation (Admin only)</p>
          </div>

          <button
            onClick={() => setIsSlideOpen(true)}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm rounded-lg flex items-center gap-2 transition-colors cursor-pointer shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Therapist</span>
          </button>
        </div>

        {/* Blocked state alert per Section 9.13 & Q5/Q6 */}
        <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <div className="text-xs text-amber-800 dark:text-amber-200">
            <p className="font-bold">Blocked Feature — Backend Endpoints Unconfirmed (Q5/Q6)</p>
            <p className="mt-0.5">Therapist directory endpoint & salary fields pending backend confirmation. Displaying shell UI with stubbed data layer.</p>
          </div>
        </div>

        <DataTable columns={columns} data={therapists} />

        {/* Add Therapist Drawer */}
        <SlideOver isOpen={isSlideOpen} onClose={() => setIsSlideOpen(false)} title="Add Therapist / Doctor" subtitle="Create new practitioner profile">
          <form onSubmit={handleCreateTherapist} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">First Name *</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Ananya"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Last Name *</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Roy"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-lg text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Email Address *</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ananya.roy@aarogya.com"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Phone Number</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 9876543210"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-lg text-sm"
              />
            </div>

            <div className="pt-4 border-t flex items-center justify-end gap-3">
              <button type="button" onClick={() => setIsSlideOpen(false)} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">
                Cancel
              </button>
              <button type="submit" className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg">
                Save Therapist
              </button>
            </div>
          </form>
        </SlideOver>
      </div>
    </AppShell>
  );
}
