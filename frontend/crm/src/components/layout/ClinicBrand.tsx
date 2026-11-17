'use client';

import React from 'react';

/**
 * Clinic logo on the left of the top bar (D-030). When the clinic has no logo,
 * or the saved logo no longer loads, the clinic name is shown instead.
 */
export function ClinicBrand({ logoUrl, name }: { logoUrl?: string | null; name?: string | null }) {
  const [broken, setBroken] = React.useState(false);

  // A new logo (saved in Settings, or another clinic) gets a fresh try.
  React.useEffect(() => setBroken(false), [logoUrl]);

  const label = name || 'Your clinic';

  if (logoUrl && !broken) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt={label}
        title={label}
        onError={() => setBroken(true)}
        className="h-9 w-auto max-w-[120px] shrink-0 object-contain md:max-w-[180px]"
      />
    );
  }

  return (
    <span
      title={label}
      className="min-w-0 max-w-[140px] shrink truncate font-display text-[15px] font-bold tracking-tight text-ink md:max-w-[240px] dark:text-slate-100"
    >
      {label}
    </span>
  );
}

/** AV Suite brand on the right of the top bar: wordmark, or only the mark on phones. */
export function AvBrand() {
  return (
    <span className="flex shrink-0 items-center" title="AV Suite">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/av-logo-wordmark.png" alt="AV Suite" className="hidden h-7 w-auto sm:block" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/av-logo-mark.png" alt="AV Suite" className="h-8 w-8 object-contain sm:hidden" />
    </span>
  );
}
