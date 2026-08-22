import React, { useEffect, useState } from 'react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useUserPermissions, useUpdateUserPermissions } from '../api';
import { User } from '../../../types/api';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
}

const CAPABILITIES = [
  { key: 'patients.view', label: 'View Patients', scopes: ['none', 'own', 'all'] },
  { key: 'patients.create', label: 'Create Patients', scopes: ['none', 'all'] },
  { key: 'patients.edit', label: 'Edit Patients', scopes: ['none', 'own', 'all'] },
  { key: 'patients.delete', label: 'Delete Patients', scopes: ['none', 'all'] },
  { key: 'appointments.view', label: 'View Appointments', scopes: ['none', 'own', 'all'] },
  { key: 'appointments.create', label: 'Create Appointments', scopes: ['none', 'own', 'all'] },
  { key: 'appointments.edit', label: 'Edit Appointments', scopes: ['none', 'own', 'all'] },
  { key: 'treatments.view', label: 'View Treatments', scopes: ['none', 'own', 'all'] },
  { key: 'treatments.create', label: 'Create Treatments', scopes: ['none', 'own', 'all'] },
  { key: 'treatments.edit', label: 'Edit Treatments', scopes: ['none', 'own', 'all'] },
  { key: 'analytics.my_performance', label: 'Analytics: My Performance', scopes: ['none', 'own'] },
  { key: 'analytics.clinic_financials', label: 'Analytics: Clinic Financials', scopes: ['none', 'all'] },
  { key: 'users.manage', label: 'Manage Users', scopes: ['none', 'all'] },
  { key: 'permissions.manage', label: 'Manage Permissions', scopes: ['none', 'all'] },
  { key: 'leads.view', label: 'View Leads', scopes: ['none', 'own', 'all'] },
  { key: 'leads.create', label: 'Create Leads', scopes: ['none', 'own', 'all'] },
  { key: 'leads.edit', label: 'Edit Leads', scopes: ['none', 'own', 'all'] },
  { key: 'leads.delete', label: 'Delete Leads', scopes: ['none', 'all'] },
  { key: 'billing.view', label: 'View Billing', scopes: ['none', 'all'] },
  { key: 'billing.create', label: 'Create Billing', scopes: ['none', 'all'] },
  { key: 'billing.edit', label: 'Edit Billing', scopes: ['none', 'all'] },
  { key: 'billing.delete', label: 'Delete Billing', scopes: ['none', 'all'] },
  { key: 'documents.view', label: 'View Documents', scopes: ['none', 'own', 'all'] },
  { key: 'documents.upload', label: 'Upload Documents', scopes: ['none', 'own', 'all'] },
  { key: 'documents.delete', label: 'Delete Documents', scopes: ['none', 'all'] },
  { key: 'settings.manage', label: 'Manage Settings', scopes: ['none', 'all'] },
  { key: 'booking.manage', label: 'Manage Booking', scopes: ['none', 'all'] },
  { key: 'packages.manage', label: 'Manage Packages', scopes: ['none', 'all'] },
  { key: 'exercises.manage', label: 'Manage Exercises', scopes: ['none', 'all'] },
  { key: 'posture.manage', label: 'Manage Posture', scopes: ['none', 'all'] },
  { key: 'prescriptions.manage', label: 'Manage Prescriptions', scopes: ['none', 'all'] },
];

export function UserPermissionsSlideOver({ isOpen, onClose, user }: Props) {
  const { data: permissions, isLoading } = useUserPermissions(user?.id || '');
  const updatePermissions = useUpdateUserPermissions();
  
  // Local state to track selected scopes for capabilities
  const [localPerms, setLocalPerms] = useState<Record<string, string>>({});

  useEffect(() => {
    if (permissions && Array.isArray(permissions)) {
      const permsMap: Record<string, string> = {};
      permissions.forEach((p: any) => {
        permsMap[p.capability_key] = p.scope;
      });
      setLocalPerms(permsMap);
    } else {
      setLocalPerms({});
    }
  }, [permissions, isOpen]);

  const handleScopeChange = (key: string, scope: string) => {
    setLocalPerms((prev) => ({
      ...prev,
      [key]: scope,
    }));
  };

  const handleSave = async () => {
    if (!user) return;
    
    // Filter out "none" or undefined to match backend expectation?
    // Actually backend payload expects list of { capability_key, scope }
    const payload = Object.entries(localPerms)
      .filter(([_, scope]) => scope && scope !== 'none')
      .map(([key, scope]) => ({
        capability_key: key,
        scope: scope,
      }));

    updatePermissions.mutate(
      { userId: user.id, permissions: payload },
      {
        onSuccess: () => {
          toast.success('Permissions updated successfully!');
          onClose();
        },
        onError: (err: any) => {
          toast.error(err?.message || 'Failed to update permissions');
        },
      }
    );
  };

  if (!user) return null;

  return (
    <SlideOver
      isOpen={isOpen}
      onClose={onClose}
      title="Edit User Permissions"
      subtitle={`Manage capability scopes for ${user.first_name} ${user.last_name}`}
    >
      {isLoading ? (
        <div className="flex justify-center p-8">
          <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-3 bg-teal-50 dark:bg-teal-950/50 rounded-lg border border-teal-100 dark:border-teal-900">
            <p className="text-xs text-teal-800 dark:text-teal-200">
              Note: This overrides the default role template. If set to <strong>None</strong>, the default template value for this user's role ({user.role}) will be applied.
            </p>
          </div>

          <div className="space-y-4">
            {CAPABILITIES.map((cap) => (
              <div key={cap.key} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-100 dark:border-slate-800">
                <div className="flex-1">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{cap.label}</p>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{cap.key}</p>
                </div>
                <div className="w-full sm:w-32">
                  <select
                    value={localPerms[cap.key] || 'none'}
                    onChange={(e) => handleScopeChange(cap.key, e.target.value)}
                    className="w-full px-2 py-1.5 text-xs rounded-md bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    {cap.scopes.map((s) => (
                      <option key={s} value={s}>
                        {s.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={updatePermissions.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg flex items-center gap-2"
            >
              {updatePermissions.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Overrides
            </button>
          </div>
        </div>
      )}
    </SlideOver>
  );
}
