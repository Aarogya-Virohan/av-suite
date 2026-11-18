'use client';

import { Lock } from 'lucide-react';

/**
 * Pieces shared by the patient's public pages: the screener and the
 * consent-only link (S-D-037).
 */

export const ERROR_COPY: Record<string, { title: string; body: string }> = {
  LINK_NOT_FOUND: {
    title: 'This link is not valid',
    body: 'Please check that you opened the full link, or ask your healthcare provider to send a new one.',
  },
  LINK_EXPIRED: {
    title: 'This link has expired',
    body: 'For your security, this screening link has expired. Please contact your healthcare provider to request a new link.',
  },
  LINK_CANCELLED: {
    title: 'This link is no longer active',
    body: 'Your healthcare provider has closed it. If you think this is a mistake, please contact them.',
  },
  ALREADY_COMPLETED: {
    title: 'You have already completed this screening',
    body: 'Thank you. If you need to update your answers, please contact your healthcare provider.',
  },
  ALREADY_ANSWERED: {
    title: 'You have already answered',
    body: 'Thank you. If you want to change your answer, please contact your healthcare provider.',
  },
  SCREENING_UNAVAILABLE: {
    title: 'This screening is not available right now',
    body: 'Please contact your healthcare provider directly.',
  },
  RATE_LIMITED: {
    title: 'Please wait a moment',
    body: 'There have been too many attempts from this connection. Please try again in a few minutes.',
  },
  NETWORK: {
    title: 'We could not connect',
    body: 'Please check your internet connection and try again. Any answers already sent are saved.',
  },
};

export function Shell({
  clinic,
  children,
  footer,
}: {
  clinic?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="border-b border-line bg-card/80">
        <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-[10px] bg-white p-1 shadow-card">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
          </span>
          <p className="truncate text-sm font-semibold text-ink">{clinic || 'Your clinic'}</p>
          <span className="ml-auto inline-flex items-center gap-1 text-xs text-muted">
            <Lock className="h-3.5 w-3.5" aria-hidden="true" /> Private
          </span>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 py-6 sm:py-10">{children}</main>
      {footer ? <footer className="mx-auto w-full max-w-xl px-4 pb-6">{footer}</footer> : null}
    </div>
  );
}
