'use client';

/**
 * U4 (HUB-5): full-page "access paused" screen. Same file in crm,
 * posture-tool, exercise-library and psychosocial; keep the copies
 * identical. Colours are the existing brand tokens (var() with the same
 * token value as fallback, because posture-tool does not define them all).
 */
import { SUSPENDED_DETAIL, SUSPENDED_TITLE, clearSuspended, signInUrl, useSuspended } from '../lib/suspended';

export function SuspendedScreen() {
  const level = useSuspended();
  if (!level) return null;

  const backToSignIn = () => {
    const url = signInUrl();
    clearSuspended();
    window.location.replace(url);
  };

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="av-suspended-title"
      aria-describedby="av-suspended-detail"
      data-testid="suspended-screen"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2147483000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'var(--color-canvas, #f6f2ea)',
        color: 'var(--color-ink, #141a33)',
        fontFamily: "'Inter Variable', Inter, var(--font-inter, system-ui), sans-serif",
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 440,
          padding: '32px 28px',
          borderRadius: 16,
          background: 'var(--color-card, #fffdf9)',
          border: '1px solid var(--color-line, #ebe5d8)',
          textAlign: 'center',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 48,
            height: 48,
            margin: '0 auto 16px',
            borderRadius: 999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--color-warn-wash, #f8eed9)',
            color: 'var(--color-warn, #8a5a0e)',
          }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <line x1="9" y1="6" x2="9" y2="18" />
            <line x1="15" y1="6" x2="15" y2="18" />
          </svg>
        </div>
        <h1
          id="av-suspended-title"
          style={{
            margin: 0,
            fontSize: 20,
            lineHeight: 1.35,
            fontWeight: 700,
            fontFamily: "'Plus Jakarta Sans Variable', 'Plus Jakarta Sans', var(--font-jakarta, system-ui), sans-serif",
            color: 'var(--color-midnight, #0b1238)',
          }}
        >
          {SUSPENDED_TITLE}
        </h1>
        <p id="av-suspended-detail" style={{ margin: '10px 0 24px', fontSize: 15, color: 'var(--color-muted, #5d6380)' }}>
          {SUSPENDED_DETAIL[level]}
        </p>
        <button
          type="button"
          onClick={backToSignIn}
          style={{
            width: '100%',
            minHeight: 44,
            border: 0,
            borderRadius: 10,
            cursor: 'pointer',
            fontSize: 15,
            fontWeight: 600,
            background: 'var(--color-grove, #1c7a54)',
            color: '#ffffff',
          }}
        >
          Back to sign in
        </button>
      </div>
    </div>
  );
}
