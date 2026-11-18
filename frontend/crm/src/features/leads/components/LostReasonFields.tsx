'use client';

import React from 'react';
import { FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';
import { LOST_REASONS, LOST_REMARK_MAX } from '../lostReasons';

interface LostReasonFieldsProps {
  reason: string;
  remark: string;
  onReasonChange: (value: string) => void;
  onRemarkChange: (value: string) => void;
  error?: string | null;
  idPrefix?: string;
}

export function LostReasonFields({ reason, remark, onReasonChange, onRemarkChange, error, idPrefix = 'lost' }: LostReasonFieldsProps) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel htmlFor={`${idPrefix}-reason`}>Reason lost *</FieldLabel>
        <select
          id={`${idPrefix}-reason`}
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          className={cn(inputClass, error && !reason && 'border-danger')}
        >
          <option value="">Choose a reason</option>
          {LOST_REASONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <FieldLabel htmlFor={`${idPrefix}-remark`}>Remark{reason === 'other' ? ' *' : ''}</FieldLabel>
        <textarea
          id={`${idPrefix}-remark`}
          value={remark}
          onChange={(e) => onRemarkChange(e.target.value)}
          rows={3}
          maxLength={LOST_REMARK_MAX}
          placeholder={reason === 'other' ? 'What happened?' : 'Optional'}
          className={cn(inputClass, 'h-auto py-2')}
        />
        <p className="mt-1 text-right text-[11px] tabular-nums text-muted">
          {remark.length}/{LOST_REMARK_MAX}
        </p>
      </div>
      {error && <p className="text-xs font-medium text-danger">{error}</p>}
    </div>
  );
}
