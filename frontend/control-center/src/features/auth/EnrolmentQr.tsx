'use client';

import React, { useEffect, useState } from 'react';
import { KeyRound, Loader2 } from 'lucide-react';
import QRCode from 'qrcode';

/** The setup key inside an otpauth:// link, or null when the link is not one. */
export function secretFromOtpauth(uri: string): string | null {
  try {
    const url = new URL(uri);
    if (url.protocol !== 'otpauth:') return null;
    return url.searchParams.get('secret');
  } catch {
    return null;
  }
}

/** "ABCD EFGH ..." so a person can type the key into an authenticator by hand. */
export function groupSecret(secret: string): string {
  return secret.replace(/\s+/g, '').replace(/(.{4})/g, '$1 ').trim();
}

/**
 * First-login QR code. It is drawn in this browser from the otpauth link the
 * backend returned over the password-verified step. The link and the key are
 * kept in memory only: never written to storage, never logged, never sent on.
 */
export function EnrolmentQr({ otpauthUri }: { otpauthUri: string | null | undefined }) {
  const [image, setImage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const secret = otpauthUri ? secretFromOtpauth(otpauthUri) : null;

  useEffect(() => {
    if (!otpauthUri) return;
    let cancelled = false;
    QRCode.toDataURL(otpauthUri, { margin: 1, width: 224, errorCorrectionLevel: 'M' })
      .then((url) => {
        if (!cancelled) setImage(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [otpauthUri]);

  if (!otpauthUri) {
    return (
      <div className="mt-4 grid h-40 place-items-center rounded-xl border border-dashed border-line bg-canvas text-center text-xs text-muted">
        <span className="flex flex-col items-center gap-1.5 px-6">
          <KeyRound className="h-5 w-5 text-slate-400" />
          No QR code in mock mode. Enter any 6-digit code.
        </span>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="grid min-h-[15rem] place-items-center rounded-xl border border-line bg-white p-2">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt="QR code for your authenticator app" width={224} height={224} className="h-56 w-56" />
        ) : failed ? (
          <p className="px-6 text-center text-xs text-muted">The QR code could not be drawn. Use the setup key below.</p>
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Preparing QR code" />
        )}
      </div>
      {secret ? (
        <div>
          <p className="text-xs font-medium text-muted">Cannot scan? Enter this setup key in your app (time-based).</p>
          <p data-testid="mfa-setup-key" className="mt-1 rounded-[10px] border border-line bg-canvas px-3 py-2 font-mono text-xs tracking-wider text-ink">
            {groupSecret(secret)}
          </p>
        </div>
      ) : null}
    </div>
  );
}
