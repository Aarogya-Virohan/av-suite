'use client';

import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, CheckCircle2, Clock, CloudOff, HeartHandshake, Loader2, Lock, Phone, ShieldCheck } from 'lucide-react';
import { ApiError, publicApi } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import { PATIENT_TITLES } from '@/lib/severity';
import type { InstrumentId, Item, ScreenerQuestionnaire, ScreenerState, SubmitResult } from '@/lib/types';
import { Button } from '@/components/ui/brand';

type Phase =
  | { kind: 'loading' }
  | { kind: 'error'; code: string | null; message: string }
  | { kind: 'consent' }
  | { kind: 'intro' }
  | { kind: 'question' }
  | { kind: 'submit' }
  | { kind: 'between'; next: InstrumentId }
  | { kind: 'done' }
  | { kind: 'withdrawn' };

type SaveState = 'idle' | 'saving' | 'retrying' | 'failed';

interface PendingSave {
  instrumentId: InstrumentId;
  itemId: string;
  value: number;
}

const ERROR_COPY: Record<string, { title: string; body: string }> = {
  LINK_NOT_FOUND: {
    title: 'This link is not valid',
    body: 'Please check that you opened the full link, or ask your physiotherapist to send a new one.',
  },
  LINK_EXPIRED: {
    title: 'This link has expired',
    body: 'For your privacy, links stop working after a few days. Please ask your physiotherapist for a new one.',
  },
  LINK_CANCELLED: {
    title: 'This link is no longer active',
    body: 'Your physiotherapist has closed it. If you think this is a mistake, please contact the clinic.',
  },
  ALREADY_COMPLETED: {
    title: 'You have already answered these questions',
    body: 'Thank you. Your answers have reached your physiotherapist. There is nothing more to do here.',
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

function firstOpenItem(q: ScreenerQuestionnaire): number {
  const idx = q.instrument.items.findIndex((it) => !(it.id in q.answers));
  return idx === -1 ? q.instrument.items.length : idx;
}

function scoredDone(q: ScreenerQuestionnaire): boolean {
  return q.instrument.items.every((it) => !it.scored || it.id in q.answers);
}

function SupportCard() {
  return (
    <section aria-labelledby="support-h" className="rounded-2xl border border-logo-teal/40 bg-logo-teal-wash p-5 text-ink">
      <div className="flex items-center gap-2 text-logo-teal-ink">
        <HeartHandshake className="h-5 w-5" aria-hidden="true" />
        <h2 id="support-h" className="font-display text-[17px] font-bold">
          You don&apos;t have to face this alone
        </h2>
      </div>
      <p className="mt-2 text-[15px] leading-relaxed text-ink-2">
        If you are having thoughts of harming yourself, please talk to someone today. Tele-MANAS, the Government
        of India&apos;s free mental health helpline, is open 24 hours and speaks many Indian languages.
      </p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <a href="tel:14416" className="flex h-12 items-center justify-center gap-2 rounded-xl bg-logo-teal-ink font-semibold text-white">
          <Phone className="h-4 w-4" aria-hidden="true" /> Call 14416
        </a>
        <a href="tel:18008914416" className="flex h-12 items-center justify-center gap-2 rounded-xl border border-logo-teal-ink bg-card font-semibold text-logo-teal-ink">
          <Phone className="h-4 w-4" aria-hidden="true" /> 1-800-891-4416
        </a>
      </div>
      <p className="mt-3 text-sm text-ink-2">
        If you are in immediate danger, call <a href="tel:112" className="font-semibold underline">112</a>.
      </p>
    </section>
  );
}

function Shell({
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

export default function ScreenerPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<ScreenerState | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });
  const [qi, setQi] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const [flags, setFlags] = useState({ referral: false, support: false });
  const queue = useRef<PendingSave[]>([]);
  const draining = useRef<Promise<void> | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const fail = useCallback((err: unknown) => {
    if (err instanceof ApiError) {
      setPhase({ kind: 'error', code: err.code, message: err.message });
    } else {
      setPhase({ kind: 'error', code: null, message: 'Something went wrong.' });
    }
  }, []);

  const apply = useCallback((s: ScreenerState) => {
    setState(s);
    const idx = Math.max(0, s.questionnaires.findIndex((q) => q.instrument.id === s.current_instrument_id));
    setQi(idx);
    setSelected(null);
    if (s.consent.required) {
      setPhase({ kind: 'consent' });
      return;
    }
    const q = s.questionnaires[idx];
    const started = Object.keys(q.answers).length > 0;
    if (!started) setPhase({ kind: 'intro' });
    else if (firstOpenItem(q) >= q.instrument.items.length) setPhase({ kind: 'submit' });
    else setPhase({ kind: 'question' });
  }, []);

  const load = useCallback(
    () => publicApi.get<ScreenerState>(`/screener/${token}`).then(apply, fail),
    [token, apply, fail],
  );

  useEffect(() => {
    let alive = true;
    publicApi.get<ScreenerState>(`/screener/${token}`).then(
      (s) => alive && apply(s),
      (err) => alive && fail(err),
    );
    return () => {
      alive = false;
    };
  }, [token, apply, fail]);

  const reload = () => {
    setPhase({ kind: 'loading' });
    void load();
  };

  const q = state?.questionnaires[qi] ?? null;
  const itemIndex = q ? firstOpenItem(q) : 0;
  const item: Item | null = q && itemIndex < q.instrument.items.length ? q.instrument.items[itemIndex] : null;
  const options = item ? item.options ?? q!.instrument.options : [];
  const scoredCount = q ? q.instrument.items.filter((i) => i.scored).length : 0;
  const multi = (state?.questionnaires.length ?? 0) > 1;

  useEffect(() => {
    headingRef.current?.focus();
  }, [phase.kind, itemIndex, qi]);

  // Sequential, retried auto-save. The patient moves on at once; answers
  // are sent in order in the background (SRS 3.4 and 3.5).
  const drain = useCallback(async () => {
    if (draining.current) return draining.current;
    const run = async () => {
      while (queue.current.length) {
        const next = queue.current[0];
        let attempt = 0;
        for (;;) {
          setSaveState(attempt === 0 ? 'saving' : 'retrying');
          try {
            await publicApi.post(`/screener/${token}/answers`, {
              instrument_id: next.instrumentId,
              item_id: next.itemId,
              value: next.value,
            });
            queue.current.shift();
            break;
          } catch (err) {
            const e = err as ApiError;
            const transient = e.status === 0 || e.status >= 500 || e.status === 429;
            if (transient && attempt < 6) {
              attempt += 1;
              await new Promise((r) => setTimeout(r, Math.min(8000, 600 * 2 ** attempt)));
              continue;
            }
            queue.current = [];
            setSaveState('failed');
            if (e.code === 'ANSWER_LOCKED' || e.code === 'OUT_OF_ORDER') {
              await load(); // the server is the source of truth
              return;
            }
            fail(err);
            return;
          }
        }
      }
      setSaveState('idle');
    };
    draining.current = run().finally(() => {
      draining.current = null;
    });
    return draining.current;
  }, [token, load, fail]);

  function answer(value: number | null) {
    if (!state || !q || !item) return;
    if (value !== null) {
      const updated = { ...q, answers: { ...q.answers, [item.id]: value } };
      const qs = state.questionnaires.map((x, i) => (i === qi ? updated : x));
      setState({ ...state, questionnaires: qs });
      queue.current.push({ instrumentId: q.instrument.id, itemId: item.id, value });
      void drain();
      const nextOpen = firstOpenItem(updated);
      setSelected(null);
      if (nextOpen >= updated.instrument.items.length) setPhase({ kind: 'submit' });
    } else {
      // Skipping the optional, unscored difficulty question.
      setSelected(null);
      setPhase({ kind: 'submit' });
    }
  }

  async function giveConsent() {
    if (!state) return;
    setBusy(true);
    try {
      await publicApi.post(`/screener/${token}/consent`, { text_version: state.consent.text_version });
      setState({ ...state, consent: { ...state.consent, required: false } });
      setPhase({ kind: 'intro' });
    } catch (err) {
      if (err instanceof ApiError && err.code === 'CONSENT_TEXT_CHANGED') await load();
      else fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function withdraw() {
    setBusy(true);
    try {
      await publicApi.post(`/screener/${token}/withdraw`);
      queue.current = [];
      setPhase({ kind: 'withdrawn' });
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
      setConfirmWithdraw(false);
    }
  }

  async function submit() {
    if (!state || !q) return;
    setBusy(true);
    try {
      await drain();
      if (queue.current.length) return;
      const res = await publicApi.post<SubmitResult>(`/screener/${token}/submit`, { instrument_id: q.instrument.id });
      setFlags({ referral: res.show_referral_message, support: res.show_support_contacts });
      const qs = state.questionnaires.map((x, i) => (i === qi ? { ...x, status: 'completed' as const } : x));
      setState({ ...state, questionnaires: qs });
      if (res.assignment_complete || !res.next_instrument_id) {
        setPhase({ kind: 'done' });
      } else {
        setPhase({ kind: 'between', next: res.next_instrument_id });
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) setSaveState('failed');
      else if (err instanceof ApiError && (err.code === 'INCOMPLETE' || err.code === 'OUT_OF_ORDER')) await load();
      else fail(err);
    } finally {
      setBusy(false);
    }
  }

  const onOptionKey = (e: React.KeyboardEvent, idx: number) => {
    if (!['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft'].includes(e.key)) return;
    e.preventDefault();
    const dir = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : -1;
    const next = (idx + dir + options.length) % options.length;
    setSelected(options[next].value);
    const el = document.getElementById(`opt-${next}`);
    el?.focus();
  };

  const footer = useMemo(() => {
    if (!state || ['error', 'withdrawn', 'done', 'loading'].includes(phase.kind)) return null;
    const isDass = q?.instrument.id === 'dass21';
    return (
      <div className="space-y-3 border-t border-line pt-4 text-center text-xs text-muted">
        <p className="inline-flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
          Only your physiotherapist sees your answers. Link valid until {formatDate(state.expires_at)}.
        </p>
        {isDass ? (
          <p>
            DASS-21: Lovibond &amp; Lovibond (1995).{' '}
            <a className="underline" href="https://www2.psy.unsw.edu.au/dass/" target="_blank" rel="noopener noreferrer">
              www2.psy.unsw.edu.au/dass
            </a>
          </p>
        ) : null}
        {phase.kind !== 'consent' ? (
          <p>
            <button type="button" className="cursor-pointer underline hover:text-ink" onClick={() => setConfirmWithdraw(true)}>
              Withdraw my consent
            </button>
          </p>
        ) : null}
      </div>
    );
  }, [state, phase.kind, q]);

  // ---------------------------------------------------------------- render
  if (phase.kind === 'loading') {
    return (
      <Shell>
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-grove" aria-label="Loading your questions" />
        </div>
      </Shell>
    );
  }

  if (phase.kind === 'error') {
    const copy = (phase.code && ERROR_COPY[phase.code]) || {
      title: 'Something went wrong',
      body: phase.message,
    };
    const done = phase.code === 'ALREADY_COMPLETED';
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
          {phase.code === 'NETWORK' || phase.code === 'RATE_LIMITED' || phase.code === null ? (
            <Button className="mt-6 h-12 px-6" onClick={reload}>
              Try again
            </Button>
          ) : null}
        </div>
      </Shell>
    );
  }

  if (!state || !q) return null;

  const withdrawDialog = confirmWithdraw ? (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-midnight/55 p-4 sm:items-center" role="presentation">
      <div role="alertdialog" aria-modal="true" aria-labelledby="wd-title" aria-describedby="wd-body" className="w-full max-w-md rounded-2xl bg-card p-6 shadow-2xl">
        <h2 id="wd-title" className="font-display text-lg font-bold text-ink">
          Withdraw your consent?
        </h2>
        <p id="wd-body" className="mt-2 text-[15px] text-ink-2">
          Your clinic will not send you these questionnaires again. Answers you have already submitted stay with
          your physiotherapist unless you ask the clinic to delete them.
        </p>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" className="h-12" onClick={() => setConfirmWithdraw(false)} autoFocus>
            Keep going
          </Button>
          <Button className="h-12 border-danger bg-none bg-danger hover:bg-danger" onClick={withdraw} disabled={busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Withdraw
          </Button>
        </div>
      </div>
    </div>
  ) : null;

  if (phase.kind === 'withdrawn') {
    return (
      <Shell clinic={state.clinic_name}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 text-center shadow-card sm:p-8">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-ink-2">
            <Check className="h-6 w-6" />
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
            Your consent has been withdrawn
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-ink-2">
            You will not be sent these questionnaires again. You can still talk to your physiotherapist about how
            you are feeling at any time.
          </p>
        </div>
      </Shell>
    );
  }

  if (phase.kind === 'consent') {
    return (
      <Shell clinic={state.clinic_name} footer={footer}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
          <h1 ref={headingRef} tabIndex={-1} className="font-display text-2xl font-bold tracking-tight text-ink outline-none">
            {state.consent.title}
          </h1>
          <div className="mt-4 space-y-3 text-[15px] leading-relaxed text-ink-2">
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
            <span className="text-[15px] font-semibold text-ink">I have read this and I agree to answer the questions.</span>
          </label>
          <div className="mt-6 flex flex-col gap-3">
            <Button className="h-12 text-base" disabled={!agree || busy} onClick={giveConsent}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Continue
            </Button>
            <Button variant="ghost" className="h-12" onClick={() => setConfirmWithdraw(true)}>
              I don&apos;t want to take part
            </Button>
          </div>
        </div>
        {withdrawDialog}
      </Shell>
    );
  }

  const title = PATIENT_TITLES[q.instrument.id];
  const partLabel = multi ? `Part ${qi + 1} of ${state.questionnaires.length}` : null;

  if (phase.kind === 'intro') {
    return (
      <Shell clinic={state.clinic_name} footer={footer}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
          {partLabel ? <p className="text-xs font-semibold uppercase tracking-wide text-grove">{partLabel}</p> : null}
          <h1 ref={headingRef} tabIndex={-1} className="mt-1 font-display text-2xl font-bold tracking-tight text-ink outline-none">
            {title.title}
          </h1>
          <p className="mt-2 text-[15px] text-ink-2">{title.blurb}</p>
          <ul className="mt-5 space-y-2 text-[15px] text-ink-2">
            <li className="flex gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-grove" aria-hidden="true" />
              {scoredCount} short questions, about {title.minutes} minutes
            </li>
            <li className="flex gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-grove" aria-hidden="true" />
              There are no right or wrong answers
            </li>
            <li className="flex gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-grove" aria-hidden="true" />
              Each answer is saved as you go, so you can stop and come back with the same link
            </li>
            <li className="flex gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-grove" aria-hidden="true" />
              Once you move to the next question, you can&apos;t go back and change an answer
            </li>
          </ul>
          <Button className="mt-7 h-12 w-full text-base" onClick={() => setPhase({ kind: 'question' })}>
            Start
          </Button>
        </div>
        {withdrawDialog}
      </Shell>
    );
  }

  if (phase.kind === 'between') {
    const next = state.questionnaires.find((x) => x.instrument.id === phase.next)!;
    const nt = PATIENT_TITLES[phase.next];
    return (
      <Shell clinic={state.clinic_name} footer={footer}>
        <div className="space-y-4">
          <div className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
            <span className="grid h-11 w-11 place-items-center rounded-full bg-grove-wash text-grove">
              <Check className="h-5 w-5" />
            </span>
            <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
              Thank you, that part is done
            </h1>
            <p className="mt-2 text-[15px] text-ink-2">
              Next: <span className="font-semibold text-ink">{nt.title}</span>.{' '}
              {next.instrument.items.filter((i) => i.scored).length} questions, about {nt.minutes} minutes.
            </p>
            <Button
              className="mt-6 h-12 w-full text-base"
              onClick={() => {
                const idx = state.questionnaires.findIndex((x) => x.instrument.id === phase.next);
                setQi(idx);
                setPhase({ kind: 'intro' });
              }}
            >
              Continue
            </Button>
          </div>
          {flags.support ? <SupportCard /> : null}
        </div>
        {withdrawDialog}
      </Shell>
    );
  }

  if (phase.kind === 'done') {
    return (
      <Shell clinic={state.clinic_name}>
        <div className="space-y-4">
          <div className="animate-rise rounded-2xl border border-line bg-card p-6 text-center shadow-card sm:p-8">
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-grove-wash text-grove">
              <CheckCircle2 className="h-7 w-7" />
            </span>
            <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-2xl font-bold text-ink outline-none">
              Thank you
            </h1>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-2">
              Your answers have been sent to your physiotherapist. You can close this page.
            </p>
            {flags.referral ? (
              <p className="mt-4 rounded-xl bg-canvas p-4 text-left text-[15px] leading-relaxed text-ink-2">
                Some of your answers suggest it may help to talk things through. Your physiotherapist may bring
                this up at your next visit, and you are welcome to raise it yourself or call the clinic sooner.
              </p>
            ) : null}
          </div>
          {flags.support ? <SupportCard /> : null}
        </div>
      </Shell>
    );
  }

  if (phase.kind === 'submit') {
    return (
      <Shell clinic={state.clinic_name} footer={footer}>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
          {partLabel ? <p className="text-xs font-semibold uppercase tracking-wide text-grove">{partLabel}</p> : null}
          <h1 ref={headingRef} tabIndex={-1} className="mt-1 font-display text-xl font-bold text-ink outline-none">
            All questions answered
          </h1>
          <p className="mt-2 text-[15px] text-ink-2">Send your answers to your physiotherapist.</p>
          {saveState === 'failed' ? (
            <p role="alert" className="mt-4 flex items-center gap-2 rounded-xl bg-warn-wash p-3 text-sm text-warn">
              <CloudOff className="h-4 w-4 shrink-0" /> We could not reach the server. Check your connection and press Send again.
            </p>
          ) : null}
          <Button className="mt-6 h-12 w-full text-base" onClick={submit} disabled={busy || !scoredDone(q)}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Send answers
          </Button>
        </div>
        {withdrawDialog}
      </Shell>
    );
  }

  // phase.kind === 'question'
  if (!item) return null;
  const answeredScored = q.instrument.items.slice(0, itemIndex).filter((i) => i.scored).length;
  const progress = Math.round((answeredScored / scoredCount) * 100);
  const questionId = `q-${item.id}`;

  return (
    <Shell clinic={state.clinic_name} footer={footer}>
      <div className="flex flex-1 flex-col">
        <div className="mb-5">
          <div className="flex items-center justify-between text-sm font-semibold text-ink-2">
            <span aria-live="polite">
              {item.scored ? `Question ${item.number} of ${scoredCount}` : 'One last, optional question'}
            </span>
            <span className="text-xs text-muted">{partLabel ?? title.title}</span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"
            role="progressbar"
            aria-label="Progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <div className="h-full rounded-full bg-grove transition-[width] duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div key={item.id} className="animate-rise rounded-2xl border border-line bg-card p-5 shadow-card sm:p-7">
          {item.scored ? <p className="text-sm text-muted">{q.instrument.instructions}</p> : null}
          <h1
            id={questionId}
            ref={headingRef}
            tabIndex={-1}
            className="mt-2 font-display text-[21px] font-bold leading-snug tracking-tight text-ink outline-none sm:text-[23px]"
          >
            {item.text}
          </h1>

          <div role="radiogroup" aria-labelledby={questionId} className="mt-5 space-y-2.5">
            {options.map((o, idx) => {
              const on = selected === o.value;
              const tabbable = selected === null ? idx === 0 : on;
              return (
                <button
                  key={o.value}
                  id={`opt-${idx}`}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  tabIndex={tabbable ? 0 : -1}
                  onClick={() => setSelected(o.value)}
                  onKeyDown={(e) => onOptionKey(e, idx)}
                  className={cn(
                    'flex min-h-14 w-full cursor-pointer items-center gap-3 rounded-xl border-2 px-4 py-3 text-left text-[16px] font-semibold transition-colors',
                    on ? 'border-grove bg-grove-wash text-ink' : 'border-line bg-card text-ink-2 hover:border-slate-300',
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      'grid h-6 w-6 shrink-0 place-items-center rounded-full border-2',
                      on ? 'border-grove bg-grove text-white' : 'border-slate-300',
                    )}
                  >
                    {on ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : null}
                  </span>
                  {o.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="sticky bottom-0 -mx-4 mt-auto bg-gradient-to-t from-canvas via-canvas to-canvas/0 px-4 pb-2 pt-6">
          <Button className="h-12 w-full text-base" disabled={selected === null} onClick={() => answer(selected)}>
            {itemIndex + 1 >= q.instrument.items.length ? 'Finish' : 'Next'}
          </Button>
          {!item.scored ? (
            <Button variant="ghost" className="mt-2 h-12 w-full" onClick={() => answer(null)}>
              Skip this question
            </Button>
          ) : null}
          <p className="mt-2 h-5 text-center text-xs text-muted" aria-live="polite">
            {saveState === 'saving' ? 'Saving…' : saveState === 'retrying' ? 'Connection is slow, still saving…' : saveState === 'idle' && itemIndex > 0 ? 'All answers saved' : ''}
          </p>
        </div>
      </div>
      {withdrawDialog}
    </Shell>
  );
}
