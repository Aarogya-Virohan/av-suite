'use client';

import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** What is about to happen, in one or two plain lines. */
  summary: React.ReactNode;
  confirmLabel: string;
  minLength?: number;
  isPending: boolean;
  onConfirm: (reason: string) => Promise<void>;
}

/** Asks for a written reason before a void / cancel. The reason goes to the audit log. */
export function ReasonSlideOver({ isOpen, onClose, title, subtitle, summary, confirmLabel, minLength = 5, isPending, onConfirm }: Props) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      setReason('');
      setError('');
    }
  }, [isOpen]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = reason.trim();
    if (clean.length < minLength) {
      setError(`Write a reason of at least ${minLength} characters`);
      return;
    }
    await onConfirm(clean);
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title={title} subtitle={subtitle}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div className="rounded-xl border border-line bg-canvas p-4 text-sm text-ink-2">{summary}</div>
        <div>
          <FieldLabel htmlFor="reason-text">Reason *</FieldLabel>
          <textarea
            id="reason-text"
            rows={3}
            maxLength={2000}
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError('');
            }}
            aria-invalid={Boolean(error)}
            placeholder="e.g. Entered twice by mistake"
            className={cn(inputClass, 'h-auto resize-none py-2', error && 'border-danger')}
          />
          <p className={error ? 'mt-1.5 text-xs font-medium text-danger' : 'mt-1.5 text-xs text-muted'}>
            {error || 'Saved in the audit log. This cannot be undone.'}
          </p>
        </div>
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Back
          </Button>
          <Button type="submit" disabled={isPending} className="border-danger bg-danger bg-none shadow-none hover:bg-danger/90">
            {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>{confirmLabel}</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
