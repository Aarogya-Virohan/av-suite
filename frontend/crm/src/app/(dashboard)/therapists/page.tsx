'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useAuthStore } from '../../../store';
import { canAccessModule } from '../../../config/permissions';
import { useUsers, useCreateUser } from '../../../features/users/api';
import { User } from '../../../types/api';
import { AlertCircle, Plus, Edit, DollarSign } from 'lucide-react';
import { toast } from 'sonner';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';

export default function TherapistsPage() {
  const role = useAuthStore((s) => s.role);
  const { data: usersResponse, isLoading } = useUsers();
  const users = usersResponse || [];
  const therapists = users.filter((u: User) => u.role === 'therapist');
  const createUser = useCreateUser();

  const [isSlideOpen, setIsSlideOpen] = useState(false);

  // Form fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  const handleCreateTherapist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName || !lastName || !email || !password) {
      toast.error('First Name, Last Name, Email, and Password are required');
      return;
    }

    try {
      await createUser.mutateAsync({
        first_name: firstName,
        last_name: lastName,
        email,
        phone: phone || undefined,
        password,
        role: 'therapist',
        is_active: true,
      });
      toast.success(`Therapist ${firstName} ${lastName} created successfully!`);
      setIsSlideOpen(false);
      setFirstName('');
      setLastName('');
      setEmail('');
      setPhone('');
      setPassword('');
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create therapist');
    }
  };

  if (!canAccessModule(role, 'therapists')) {
    return <AccessRestricted message="Therapists directory and payroll is restricted to Administrators only." />;
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
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Password *</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
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
              <button
                type="submit"
                disabled={createUser.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg disabled:opacity-50"
              >
                {createUser.isPending ? 'Creating...' : 'Save Therapist'}
              </button>
            </div>
          </form>
        </SlideOver>
      </div>
    </AppShell>
  );
}
