import React, { useEffect, useState } from 'react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { useUserPermissions, useUpdateUserPermissions } from '../api';
import { User } from '../../../types/api';
import { toast } from 'sonner';
import { AlertTriangle, Loader2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
}

import { CANONICAL_CAPABILITIES } from '../../../config/permissions';

import { useAuthStore } from '../../../store';

export function UserPermissionsSlideOver({ isOpen, onClose, user }: Props) {
  const {
    data: permissions,
    isLoading,
    isFetching,
    refetch,
  } = useUserPermissions(user?.id || '');
  const updatePermissions = useUpdateUserPermissions();
  
  // Local state to track selected scopes for capabilities
  const [localPerms, setLocalPerms] = useState<Record<string, string>>({});

  // PUT /users/{id}/permissions replaces every saved override, so the form is only
  // usable once the saved overrides are loaded. Without them, a save would overwrite
  // keys this form does not list (for example Tool 03 screening keys) with defaults.
  const savedLoaded = Array.isArray(permissions);

  useEffect(() => {
    if (permissions && Array.isArray(permissions)) {
      const permsMap: Record<string, string> = {};
      // Initialize with default for role (admin defaults to all/own, other roles default to none)
      CANONICAL_CAPABILITIES.forEach((cap) => {
        permsMap[cap.key] = user?.role === 'admin' ? (cap.allowedScopes.includes('all') ? 'all' : 'own') : 'none';
      });
      // Override with existing saved permissions from user_permissions table
      permissions.forEach((p: any) => {
        permsMap[p.capability_key] = p.scope;
      });
      setLocalPerms(permsMap);
    } else {
      setLocalPerms({});
    }
  }, [permissions, isOpen, user]);

  const handleScopeChange = (key: string, scope: string) => {
    setLocalPerms((prev) => ({
      ...prev,
      [key]: scope,
    }));
  };

  const handleSave = async () => {
    if (!user || !savedLoaded) return;

    // Explicitly send all selected scopes including 'none'
    const payload = Object.entries(localPerms)
      .filter(([_, scope]) => Boolean(scope))
      .map(([key, scope]) => ({
        capability_key: key,
        scope: scope,
      }));

    updatePermissions.mutate(
      { userId: user.id, permissions: payload },
      {
        onSuccess: () => {
          toast.success('Permissions updated successfully!');
          // If the edited user is the current logged-in user, refresh auth state
          if (useAuthStore.getState().userId === user.id) {
            useAuthStore.getState().fetchMe();
          }
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
        <div className="flex justify-center p-8" role="status" aria-label="Loading permissions">
          <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
        </div>
      ) : !savedLoaded ? (
        <div className="space-y-4">
          <div
            role="alert"
            className="flex gap-3 p-4 bg-rose-50 dark:bg-rose-950/40 rounded-lg border border-rose-200 dark:border-rose-900"
          >
            <AlertTriangle className="w-5 h-5 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-semibold text-rose-800 dark:text-rose-200">
                Could not load this user&apos;s saved permissions.
              </p>
              <p className="mt-1 text-xs text-rose-700 dark:text-rose-300">
                Editing is turned off until they load, so no saved permission is overwritten. Check your connection and try again.
              </p>
            </div>
          </div>
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Close
            </button>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-60 rounded-lg flex items-center gap-2"
            >
              {isFetching && <Loader2 className="w-4 h-4 animate-spin" />}
              Try again
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-3 bg-teal-50 dark:bg-teal-950/50 rounded-lg border border-teal-100 dark:border-teal-900">
            <p className="text-xs text-teal-800 dark:text-teal-200">
              Note: Explicitly configure capability scopes for this user. If set to <strong>None</strong>, access to that feature is completely blocked.
            </p>
          </div>

          <div className="space-y-4">
            {CANONICAL_CAPABILITIES.map((cap) => (
              <div key={cap.key} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-100 dark:border-slate-800">
                <div className="flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      {cap.module}
                    </span>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{cap.label}</p>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{cap.key}</p>
                </div>
                <div className="w-full sm:w-32">
                  <select
                    value={localPerms[cap.key] || 'none'}
                    onChange={(e) => handleScopeChange(cap.key, e.target.value)}
                    className="w-full px-2 py-1.5 text-xs rounded-md bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    {cap.allowedScopes.map((s) => (
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
              disabled={updatePermissions.isPending || !savedLoaded}
              className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-60 rounded-lg flex items-center gap-2"
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
