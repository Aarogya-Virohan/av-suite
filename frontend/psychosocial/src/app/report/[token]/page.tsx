'use client';

import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Clock, CloudOff, ExternalLink, Loader2, Lock, Phone } from 'lucide-react';
import { ApiError, publicApi } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format';
import type { PatientReport, ReportGate } from '@/lib/types';
import { Button, FieldLabel, inputClass } from '@/components/ui/brand';
import { ERROR_COPY, Shell } from '@/components/screening/public';

type Phase =
  | { kind: 'loading' }
  | { kind: 'error'; code: string | null; message: string }
  | { kind: 'verify'; gate: ReportGate; attemptsLeft: number | null }
  | { kind: 'report'; report: PatientReport };

const REPORT_ERRORS: Record<string, { title: string; body: string }> = {
  LINK_LOCKED: {
    title: 'This link is locked',
    body: 'For your privacy, the link was locked after several tries. Please ask your healthcare provider to share it again.',
  },
  LINK_CANCELLED: {
    title: 'This link is no longer active',
    body: 'Your healthcare provider has stopped sharing it. Please contact them if you need it again.',
  },
  LINK_EXPIRED: {
    title: 'This link has expired',
    body: 'For your security, report links stop working after a while. Please ask your healthcare provider to share it again.',
  },
};

/**
 * Report the provider shared after the consultation (founders' F2 follow-up,
 * S-D-039). Order is the founders': advice first, then the plain score
 * summary, then resources. No flags, band names or answers ever reach this page.
 */
export default function SharedReportPage() {
  const { token } = useParams<{ token: string }>();
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });
  const [year, setYear] = useState('');
  const [busy, setBusy] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const clinic = phase.kind === 'verify' ? phase.gate.clinic_name : phase.kind === 'report' ? phase.report.clinic_name : undefined;

  const fail = (e: unknown) =>
    setPhase(
      e instanceof ApiError ? { kind: 'error', code: e.code, message: e.message } : { kind: 'error', code: null, message: 'Something went wrong.' },
    );

  const open = async (birthYear: number | null, gate: ReportGate) => {
    setBusy(true);
    try {
      const report = await publicApi.post<PatientReport>(`/screener/report/${token}/open`, { birth_year: birthYear });
      setPhase({ kind: 'report', report });
    } catch (e) {
      if (e instanceof ApiError && e.code === 'WRONG_BIRTH_YEAR') {
        const left = (e.details as { attempts_left?: number } | undefined)?.attempts_left ?? null;
        setPhase({ kind: 'verify', gate, attemptsLeft: left });
      } else fail(e);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    let alive = true;
    publicApi.get<ReportGate>(`/screener/report/${token}`).then(
      (gate) => {
        if (!alive) return;
        if (gate.needs_birth_year) setPhase({ kind: 'verify', gate, attemptsLeft: null });
        else void open(null, gate);
      },
      (e) => alive && fail(e),
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per token
  }, [token]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [phase.kind]);

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
    const copy = (phase.code && (REPORT_ERRORS[phase.code] ?? ERROR_COPY[phase.code])) || { title: 'Something went wrong', body: phase.message };
    const retry = phase.code === null || phase.code === 'NETWORK' || phase.code === 'RATE_LIMITED';
    return (
      <Shell>
        <div className="animate-rise rounded-2xl border border-line bg-card p-6 text-center shadow-card sm:p-8">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-warn-wash text-warn">
            {phase.code === 'LINK_LOCKED' ? <Lock className="h-6 w-6" /> : phase.code === 'NETWORK' ? <CloudOff className="h-6 w-6" /> : <Clock className="h-6 w-6" />}
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
            {copy.title}
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{copy.body}</p>
          {retry ? (
            <Button className="mt-6 h-12 px-6" onClick={() => window.location.reload()}>
              Try again
            </Button>
          ) : null}
        </div>
      </Shell>
    );
  }

  if (phase.kind === 'verify') {
    const valid = /^\d{4}$/.test(year);
    return (
      <Shell clinic={clinic}>
        <form
          className="animate-rise rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8"
          onSubmit={(e) => {
            e.preventDefault();
            if (valid) void open(Number(year), phase.gate);
          }}
        >
          <span className="grid h-12 w-12 place-items-center rounded-full bg-grove-wash text-grove">
            <Lock className="h-6 w-6" />
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-xl font-bold text-ink outline-none">
            Your report from {phase.gate.clinic_name}
          </h1>
          <p className="mt-2 text-[15px] text-ink-2">For your privacy, please enter your year of birth to open it.</p>
          <div className="mt-5">
            <FieldLabel htmlFor="birth-year">Year of birth</FieldLabel>
            <input
              id="birth-year"
              inputMode="numeric"
              autoComplete="bday-year"
              placeholder="e.g. 1985"
              maxLength={4}
              value={year}
              onChange={(e) => setYear(e.target.value.replace(/\D/g, ''))}
              className={cn(inputClass, 'h-12 text-lg tracking-widest')}
            />
          </div>
          {phase.attemptsLeft !== null ? (
            <p role="alert" className="mt-3 rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
              That year does not match our records. {phase.attemptsLeft} {phase.attemptsLeft === 1 ? 'try' : 'tries'} left.
            </p>
          ) : null}
          <Button type="submit" className="mt-6 h-12 w-full text-base" disabled={!valid || busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Open my report
          </Button>
        </form>
      </Shell>
    );
  }

  const r = phase.report;
  return (
    <Shell clinic={r.clinic_name} footer={<p className="text-center text-xs text-muted">Screening aid only, not a diagnosis.</p>}>
      <article className="animate-rise space-y-5">
        <header className="rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
          <h1 ref={headingRef} tabIndex={-1} className="font-display text-2xl font-bold tracking-tight text-ink outline-none">
            Your care notes
          </h1>
          <p className="mt-1 text-sm text-muted">
            Shared by {r.provider_name ?? 'your healthcare provider'} on {formatDate(r.shared_on)}
          </p>
          {r.advice ? (
            <div className="mt-5 rounded-xl bg-grove-wash/60 p-4">
              <h2 className="text-sm font-semibold text-grove">From your healthcare provider</h2>
              <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed text-ink">{r.advice}</p>
            </div>
          ) : null}
        </header>

        {r.summary.length ? (
          <section aria-labelledby="summary-h" className="rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
            <h2 id="summary-h" className="font-display text-lg font-bold text-ink">
              Your screening summary
            </h2>
            <ul className="mt-4 space-y-4">
              {r.summary.map((s) => (
                <li key={s.short_name}>
                  <p className="text-[15px] font-semibold text-ink">
                    {s.short_name} score: {s.score} out of {s.max_score}
                  </p>
                  <p className="text-[15px] text-ink-2">{s.phrase}</p>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-muted">Discussed with your healthcare provider on {formatDate(r.shared_on)}.</p>
          </section>
        ) : null}

        {r.resources.length ? (
          <section aria-labelledby="res-h" className="rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
            <h2 id="res-h" className="font-display text-lg font-bold text-ink">
              Your prescribed resources
            </h2>
            <ul className="mt-4 space-y-3">
              {r.resources.map((res) => (
                <li key={res.title} className="rounded-xl border border-line-soft p-4">
                  {res.url ? (
                    <a href={res.url} target="_blank" rel="noopener noreferrer" className="group block">
                      <span className="flex items-center gap-1.5 font-semibold text-grove group-hover:underline">
                        {res.title}
                        <ExternalLink className="h-4 w-4 shrink-0" aria-hidden="true" />
                      </span>
                      {res.description ? <span className="mt-1 block text-sm text-ink-2">{res.description}</span> : null}
                      {res.domain ? <span className="mt-1 block text-xs text-muted">{res.domain}</span> : null}
                    </a>
                  ) : (
                    <>
                      <p className="font-semibold text-ink">{res.title}</p>
                      {res.description ? <p className="mt-1 text-sm text-ink-2">{res.description}</p> : null}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {res.phones.map((p) => (
                          <a
                            key={p.tel}
                            href={`tel:${p.tel}`}
                            className="inline-flex h-11 items-center gap-2 rounded-xl border border-logo-teal-ink px-4 text-sm font-semibold text-logo-teal-ink"
                          >
                            <Phone className="h-4 w-4" aria-hidden="true" />
                            Call {p.label}
                          </a>
                        ))}
                      </div>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {/* Shown to everyone, so it says nothing about any one result. */}
        <p className="px-2 text-center text-sm text-ink-2">
          If you ever need to talk to someone, Tele-MANAS is free and open 24 hours:{' '}
          <a href="tel:14416" className="font-semibold underline">
            14416
          </a>
          . In an emergency call{' '}
          <a href="tel:112" className="font-semibold underline">
            112
          </a>
          .
        </p>
      </article>
    </Shell>
  );
}
