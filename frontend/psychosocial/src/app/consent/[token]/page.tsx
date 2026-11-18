'use client';

import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Check, CheckCircle2, Clock, CloudOff, Loader2 } from 'lucide-react';
import { ApiError, publicApi } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import type { ReconsentState } from '@/lib/types';
import { Button } from '@/components/ui/brand';
import { ERROR_COPY, Shell } from '@/components/screening/public';

type Phase =
  | { kind: 'loading' }
  | { kind: 'error'; code: string | null; message: string }
  | { kind: 'ask' }
  | { kind: 'granted' }
  | { kind: 'declined' };

/**
 * Consent-only link sent after a patient withdrew (founders' Q7 = 7B). The
 * patient reads the current consent text and says yes or no on their own
 * phone. Nothing about them or their results is shown here.
 */
export default function ReconsentPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<ReconsentState | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState<'yes' | 'no' | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const show = (s: ReconsentState) => {
    setState(s);
    setPhase(s.state === 'granted' ? { kind: 'granted' } : s.state === 'declined' ? { kind: 'declined' } : { kind: 'ask' });
  };
  const fail = (err: unknown) =>
    setPhase(
      err instanceof ApiError
        ? { kind: 'error', code: err.code, message: err.message }
        : { kind: 'error', code: null, message: 'Something went wrong.' },
    );

  useEffect(() => {
    let alive = true;
    publicApi.get<ReconsentState>(`/screener/reconsent/${token}`).then(
      (s) => alive && show(s),
      (e) => alive && fail(e),
    );
    return () => {
      alive = false;
    };
  }, [token]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [phase.kind]);

  const answer = async (accept: boolean) => {
    if (!state) return;
    setBusy(accept ? 'yes' : 'no');
    try {
      show(
        await publicApi.post<ReconsentState>(`/screener/reconsent/${token}/answer`, {
          accept,
          text_version: accept ? state.consent.text_version : null,
        }),
      );
    } catch (e) {
      fail(e);
    } finally {
      setBusy(null);
    }
  };

  if (phase.kind === 'loading') {
    return (
      <Shell>
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-grove" aria-label="Loading" />
        </div>
      </Shell>
    );
  }

  if (phase.kind === 'error') {
    const copy =
      phase.code === 'CONSENT_TEXT_CHANGED'
        ? { title: 'The text has been updated', body: 'Please reload this page and read it again.' }
        : (phase.code && ERROR_COPY[phase.code]) || { title: 'Something went wrong', body: phase.message };
    const done = phase.code === 'ALREADY_ANSWERED';
    return (
      <Shell clinic={state?.clinic_name}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 text-center shadow-card sm:p-8">
          <span className={cn('mx-auto grid h-12 w-12 place-items-center rounded-full', done ? 'bg-grove-wash text-grove' : 'bg-warn-wash text-warn')}>
            {done ? <CheckCircle2 className="h-6 w-6" /> : phase.code === 'NETWORK' ? <CloudOff className="h-6 w-6" /> : <Clock className="h-6 w-6" />}
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
            {copy.title}
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{copy.body}</p>
          {phase.code === 'NETWORK' || phase.code === 'RATE_LIMITED' || phase.code === null || phase.code === 'CONSENT_TEXT_CHANGED' ? (
            <Button className="mt-6 h-12 px-6" onClick={() => window.location.reload()}>
              Try again
            </Button>
          ) : null}
        </div>
      </Shell>
    );
  }

  if (!state) return null;

  if (phase.kind === 'granted' || phase.kind === 'declined') {
    const yes = phase.kind === 'granted';
    return (
      <Shell clinic={state.clinic_name}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 text-center shadow-card sm:p-8">
          <span className={cn('mx-auto grid h-12 w-12 place-items-center rounded-full', yes ? 'bg-grove-wash text-grove' : 'bg-slate-100 text-ink-2')}>
            <Check className="h-6 w-6" />
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
            {yes ? 'Thank you, you are back in' : 'Your choice is saved'}
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-ink-2">
            {yes
              ? 'Your healthcare provider can send you the short questionnaires again. You can withdraw at any time from any questionnaire link.'
              : 'You will not be sent these questionnaires. You can still talk to your healthcare provider about how you are feeling at any time.'}
          </p>
        </div>
      </Shell>
    );
  }

  return (
    <Shell
      clinic={state.clinic_name}
      footer={<p className="text-center text-xs text-muted">This link works until {formatDate(state.expires_at)}.</p>}
    >
      <div className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
        <h1 ref={headingRef} tabIndex={-1} className="font-display text-2xl font-bold tracking-tight text-ink outline-none">
          Would you like to take part again?
        </h1>
        <p className="mt-2 text-[15px] text-ink-2">
          Earlier you chose not to answer these questions. Please read the information below and choose again.
        </p>
        <div className="mt-5 space-y-3 rounded-xl bg-canvas/60 p-4 text-[15px] leading-relaxed text-ink-2">
          {state.consent.paragraphs.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
        <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-canvas/60 p-4 focus-within:ring-2 focus-within:ring-grove/40">
          <input
            type="checkbox"
            checked={agree}
            onChange={(e) => setAgree(e.target.checked)}
            className="mt-0.5 h-6 w-6 shrink-0 cursor-pointer accent-[#1c7a54]"
          />
          <span className="text-[15px] font-semibold text-ink">I have read this and I agree to take part again.</span>
        </label>
        <div className="mt-6 flex flex-col gap-3">
          <Button className="h-12 text-base" disabled={!agree || busy !== null} onClick={() => answer(true)}>
            {busy === 'yes' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Yes, I agree
          </Button>
          <Button variant="ghost" className="h-12" disabled={busy !== null} onClick={() => answer(false)}>
            {busy === 'no' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            No, thank you
          </Button>
        </div>
      </div>
    </Shell>
  );
}
