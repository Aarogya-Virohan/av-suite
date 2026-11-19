'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';

export function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mx-auto mt-10 max-w-md space-y-3 rounded-2xl border border-line bg-card p-8 text-center shadow-card">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-warn-wash text-warn">
        <AlertTriangle className="h-6 w-6" />
      </span>
      <p className="text-sm text-ink-2">{message}</p>
      <button type="button" onClick={onRetry} className="text-xs font-semibold text-grove hover:text-grove-hover">
        Try again
      </button>
    </div>
  );
}
