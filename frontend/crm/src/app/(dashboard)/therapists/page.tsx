'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { SlideOver } from '../../../components/ui/SlideOver';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { useUsers, useCreateUser } from '../../../features/users/api';
import { User } from '../../../types/api';
import { Plus, Mail, Phone } from 'lucide-react';
import { toast } from 'sonner';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { Avatar, Badge, Button, FieldLabel, PageHeader, inputClass } from '../../../components/ui/brand';

export default function TherapistsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const hasAccess = canAccessModule('therapists');
  const canCreateTherapist = hasCapability('users.create');

  const { data: usersResponse, isLoading } = useUsers(hasAccess);
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

  if (!hasAccess) {
    // AccessRestricted renders its own AppShell.
    return <AccessRestricted message="Therapists directory is restricted for your role." />;
  }

  // The old "Monthly Salary" column showed a hardcoded Rs 35,000 for every
  // therapist. Salary is not stored by the backend, so it was removed
  // (Decisions.md D-014). Add it back only from real data.
  const columns: Column<User>[] = [
    {
      key: 'name',
      header: 'Therapist',
      render: (u) => (
        <div className="flex items-center gap-3">
          <Avatar name={`${u.first_name} ${u.last_name}`} size={34} />
          <span className="font-semibold text-ink">
            {u.first_name} {u.last_name}
          </span>
        </div>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (u) => (
        <span className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-slate-400" />
          {u.email}
        </span>
      ),
    },
    {
      key: 'phone',
      header: 'Phone',
      render: (u) =>
        u.phone ? (
          <span className="flex items-center gap-2 tabular-nums">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            {u.phone}
          </span>
        ) : (
          <span className="text-slate-400">-</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (u) => (u.is_active ? <Badge tone="ok">Active</Badge> : <Badge tone="neutral">Inactive</Badge>),
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Therapists Directory"
          subtitle="Practitioners in your clinic"
          actions={
            canCreateTherapist ? (
              <Button onClick={() => setIsSlideOpen(true)}>
                <Plus className="h-4 w-4" />
                <span>Add Therapist</span>
              </Button>
            ) : null
          }
        />

        <DataTable columns={columns} data={therapists} />

        {/* Add Therapist Drawer */}
        <SlideOver isOpen={isSlideOpen} onClose={() => setIsSlideOpen(false)} title="Add Therapist / Doctor" subtitle="Create new practitioner profile">
          <form onSubmit={handleCreateTherapist} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FieldLabel>First Name *</FieldLabel>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Ananya"
                  className={inputClass}
                />
              </div>

              <div>
                <FieldLabel>Last Name *</FieldLabel>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Roy"
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <FieldLabel>Email Address *</FieldLabel>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ananya.roy@aarogya.com"
                className={inputClass}
              />
            </div>

            <div>
              <FieldLabel>Password *</FieldLabel>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className={inputClass}
              />
            </div>

            <div>
              <FieldLabel>Phone Number</FieldLabel>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 9876543210"
                className={inputClass}
              />
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
              <Button type="button" variant="ghost" onClick={() => setIsSlideOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createUser.isPending}>
                {createUser.isPending ? 'Creating...' : 'Save Therapist'}
              </Button>
            </div>
          </form>
        </SlideOver>
      </div>
    </AppShell>
  );
}
