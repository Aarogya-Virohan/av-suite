'use client';

import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { Button } from '../../../components/ui/brand';
import type { Lead } from '../../../types/api';
import { lostReasonError } from '../lostReasons';
import { LostReasonFields } from './LostReasonFields';

interface LostReasonSlideOverProps {
  lead: Lead | null;
  saving: boolean;
  onClose: () => void;
  onSave: (reason: string, remark: string) => void;
}

/*
 * Asked when a lead is moved to Lost, and when the reason of a lost lead is
 * edited. The stage only changes after a reason is saved (Decisions.md D-026).
 */
export function LostReasonSlideOver({ lead, saving, onClose, onSave }: LostReasonSlideOverProps) {
  const [reason, setReason] = useState('');
  const [remark, setRemark] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lead) {
      setReason(lead.lost_reason ?? '');
      setRemark(lead.lost_remark ?? '');
      setError(null);
    }
  }, [lead]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const problem = lostReasonError(reason, remark);
    setError(problem);
    if (!problem) onSave(reason, remark.trim());
  };

  return (
    <SlideOver isOpen={!!lead} onClose={onClose} title={lead?.stage === 'lost' ? 'Edit lost reason' : 'Mark lead as lost'} subtitle={lead ? lead.name : undefined}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <LostReasonFields
          reason={reason}
          remark={remark}
          onReasonChange={(v) => {
            setReason(v);
            setError(null);
          }}
          onRemarkChange={(v) => {
            setRemark(v);
            setError(null);
          }}
          error={error}
        />
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Save</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
