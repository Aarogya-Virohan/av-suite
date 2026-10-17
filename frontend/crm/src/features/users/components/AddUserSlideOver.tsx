'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useCreateUser } from '../api';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

type Role = '' | 'admin' | 'therapist' | 'front_desk';

const errorText = 'mt-1.5 text-xs font-medium text-danger';

/*
 * Fixes (verified against the API):
 * - The default role was 'receptionist', which the backend rejects (roles are
 *   admin, therapist, front_desk), so creating a front-desk user always failed
 *   with 422. The value is now 'front_desk'.
 * - Role has no default: it controls permissions, so it is an explicit choice.
 * - The error toast received FastAPI's detail array (not text); it now shows
 *   the normalised message. Password length is checked before submit (min 8).
 */
export function AddUserSlideOver({ isOpen, onClose }: Props) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const createUser = useCreateUser();

  React.useEffect(() => {
    if (isOpen) {
      setFirstName('');
      setLastName('');
      setEmail('');
      setPassword('');
      setRole('');
      setErrors({});
    }
  }, [isOpen]);

  const validate = () => {
    const next: Record<string, string> = {};
    if (!firstName.trim()) next.firstName = 'First name is required';
    if (!lastName.trim()) next.lastName = 'Last name is required';
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Enter a valid email';
    if (password.length < 8) next.password = 'At least 8 characters';
    if (!role) next.role = 'Select a role';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      await createUser.mutateAsync({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
        role,
      });
      toast.success(`${firstName.trim()} ${lastName.trim()} added`);
      onClose();
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create user');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Add New User" subtitle="Create a new user account for your clinic">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="user-first">First Name *</FieldLabel>
            <input id="user-first" type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} className={cn(inputClass, errors.firstName && 'border-danger')} />
            {errors.firstName && <p className={errorText}>{errors.firstName}</p>}
          </div>
          <div>
            <FieldLabel htmlFor="user-last">Last Name *</FieldLabel>
            <input id="user-last" type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} className={cn(inputClass, errors.lastName && 'border-danger')} />
            {errors.lastName && <p className={errorText}>{errors.lastName}</p>}
          </div>
        </div>
        <div>
          <FieldLabel htmlFor="user-email">Email *</FieldLabel>
          <input id="user-email" type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} className={cn(inputClass, errors.email && 'border-danger')} />
          {errors.email && <p className={errorText}>{errors.email}</p>}
        </div>
        <div>
          <FieldLabel htmlFor="user-password">Temporary Password *</FieldLabel>
          <input
            id="user-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimum 8 characters"
            className={cn(inputClass, errors.password && 'border-danger')}
          />
          {errors.password && <p className={errorText}>{errors.password}</p>}
        </div>
        <div>
          <FieldLabel htmlFor="user-role">Role *</FieldLabel>
          <select id="user-role" value={role} onChange={(e) => setRole(e.target.value as Role)} className={cn(inputClass, errors.role && 'border-danger')}>
            <option value="">Select role…</option>
            <option value="admin">Admin</option>
            <option value="therapist">Therapist / Doctor</option>
            <option value="front_desk">Front Desk / Receptionist</option>
          </select>
          {errors.role && <p className={errorText}>{errors.role}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createUser.isPending}>
            {createUser.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>{createUser.isPending ? 'Creating...' : 'Create User'}</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
