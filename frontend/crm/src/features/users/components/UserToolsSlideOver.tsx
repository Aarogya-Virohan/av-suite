'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { Button } from '../../../components/ui/brand';
import { User } from '../../../types/api';
import { type ToolKey, enabledTools, useSetUserTools, useUserTools } from '../tools';
import { ToolCheckboxes } from './ToolCheckboxes';

/** Edit one user's 3 tool checkboxes (CRM-6). PUT sends the full list that should be on. */
export function UserToolsSlideOver({ isOpen, onClose, user }: { isOpen: boolean; onClose: () => void; user: User | null }) {
  const { data, isLoading, error } = useUserTools(user?.id, isOpen);
  const save = useSetUserTools();
  const [value, setValue] = useState<ToolKey[]>([]);

  React.useEffect(() => {
    if (isOpen && data) setValue(enabledTools(data.tools));
  }, [isOpen, data]);

  const name = user ? `${user.first_name} ${user.last_name}` : '';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    try {
      await save.mutateAsync({ userId: user.id, tools: value });
      toast.success(`Tool access saved for ${name}`);
      onClose();
    } catch (err: any) {
      toast.error(err?.message || 'Could not save tool access');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Tool Access" subtitle={name}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading tool access...
          </div>
        ) : error ? (
          <p className="text-sm font-medium text-danger">{(error as Error).message || 'Could not load tool access'}</p>
        ) : (
          <ToolCheckboxes value={value} onChange={setValue} available={data?.available} labels={data?.labels} role={data?.role ?? user?.role} />
        )}
        <p className="text-xs text-muted">
          Custom scopes set in Edit Permissions stay as they are for tools that remain ticked.
        </p>
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending || isLoading || !!error}>
            {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Save Tool Access</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
