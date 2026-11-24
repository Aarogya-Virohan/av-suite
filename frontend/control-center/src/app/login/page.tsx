'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Check, Eye, EyeOff, KeyRound, Loader2, Lock, Mail, ShieldCheck, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/brand';
import { cn } from '@/lib/cn';
import { errorMessage } from '@/lib/platform-api/errors';
import type { LoginChallenge } from '@/lib/platform-api/types';
import { useLogin, useVerifyMfa } from '@/features/auth/hooks';
import { EnrolmentQr } from '@/features/auth/EnrolmentQr';
import { useSession } from '@/store/session';
import { MockModeBadge } from '@/components/layout/MockModeBadge';

const credentialsSchema = z.object({
  email: z.string().trim().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
});
type Credentials = z.infer<typeof credentialsSchema>;

const codeSchema = z.object({
  code: z.string().trim().regex(/^\d{6}$/, 'Enter the 6-digit code from your authenticator app'),
});
type CodeForm = z.infer<typeof codeSchema>;

const fieldClass =
  'h-11 w-full rounded-[10px] border border-line bg-card pl-10 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15';

export default function LoginPage() {
  const router = useRouter();
  const hydrated = useSession((s) => s.hydrated);
  const token = useSession((s) => s.token);
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && token) router.replace('/overview');
  }, [hydrated, token, router]);

  if (!hydrated || token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-midnight">
        <div className="flex items-center gap-3 text-lime">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="text-sm font-medium">Verifying session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Brand panel, same treatment as the CRM login */}
      <div className="relative hidden overflow-hidden bg-[radial-gradient(90%_70%_at_0%_100%,rgba(27,74,84,0.95)_0%,rgba(27,74,84,0)_60%),linear-gradient(160deg,#0b1238_0%,#111c4a_55%,#0b1238_100%)] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gradient-to-br from-fresh to-[#0b665a] opacity-30 blur-2xl"
        />
        <div className="relative flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center overflow-hidden rounded-[13px] bg-white p-1.5 shadow-[0_0_0_2px_rgba(78,136,143,0.5)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
          </span>
          <div>
            <p className="font-display text-lg font-bold tracking-tight">AV Suite</p>
            <p className="text-xs text-[#aab2d6]">Control Center</p>
          </div>
        </div>

        <div className="relative max-w-md space-y-6">
          <h2 className="font-display text-[34px] font-bold leading-tight tracking-tight">
            Run the AV platform <span className="text-lime">from one console.</span>
          </h2>
          <ul className="space-y-3 text-sm text-[#c3c9e6]">
            {['Organizations, clinics and branches', 'Tool access with validity dates', 'Every change audited with a reason'].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-lime/15">
                  <Check className="h-3.5 w-3.5 text-lime" />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-[#7f88b3]">Aarogya Virohan · AV team only</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <span className="mb-5 grid h-11 w-11 place-items-center overflow-hidden rounded-xl bg-white p-1.5 shadow-card lg:hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
            </span>
            <div className="mb-3">
              <MockModeBadge />
            </div>
            <h1 className="font-display text-[28px] font-bold tracking-tight text-ink">
              {challenge ? (challenge.mfa_enrolment_required ? 'Set up two-step sign-in' : 'Two-step sign-in') : 'Super admin sign-in'}
            </h1>
            <p className="mt-1 text-sm text-muted">
              {challenge
                ? challenge.mfa_enrolment_required
                  ? 'Your account needs an authenticator app before first use.'
                  : 'Enter the code from your authenticator app.'
                : 'For AV operators only. Clinic staff sign in to the CRM.'}
            </p>
          </div>

          {formError ? (
            <p role="alert" className="mb-5 rounded-[10px] border border-danger/20 bg-danger-wash px-3 py-2.5 text-xs font-medium text-danger">
              {formError}
            </p>
          ) : null}

          {challenge ? (
            <MfaStep
              challenge={challenge}
              onError={setFormError}
              onBack={() => {
                setChallenge(null);
                setFormError(null);
              }}
              onDone={() => router.replace('/overview')}
            />
          ) : (
            <CredentialsStep
              onError={setFormError}
              onChallenge={(c) => {
                setFormError(null);
                setChallenge(c);
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function CredentialsStep({ onChallenge, onError }: { onChallenge: (c: LoginChallenge) => void; onError: (m: string | null) => void }) {
  const [showPassword, setShowPassword] = useState(false);
  const login = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Credentials>({ resolver: zodResolver(credentialsSchema) });

  const onSubmit = (values: Credentials) => {
    onError(null);
    login.mutate(values, {
      onSuccess: onChallenge,
      onError: (e) => onError(errorMessage(e)),
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div>
        <label htmlFor="login-email" className="mb-1.5 block text-xs font-semibold text-ink-2">
          Email Address
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="login-email"
            {...register('email')}
            type="email"
            autoComplete="username"
            placeholder="you@aarogyavirohan.com"
            aria-invalid={!!errors.email}
            className={cn(fieldClass, 'pr-4', errors.email && 'border-danger')}
          />
        </div>
        {errors.email && <p className="mt-1.5 text-xs font-medium text-danger">{errors.email.message}</p>}
      </div>

      <div>
        <label htmlFor="login-password" className="mb-1.5 block text-xs font-semibold text-ink-2">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="login-password"
            {...register('password')}
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={!!errors.password}
            className={cn(fieldClass, 'pr-11', errors.password && 'border-danger')}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-slate-400 transition-colors hover:text-ink"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.password && <p className="mt-1.5 text-xs font-medium text-danger">{errors.password.message}</p>}
      </div>

      <Button type="submit" disabled={login.isPending} className="h-11 w-full">
        {login.isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Checking...</span>
          </>
        ) : (
          <span>Continue</span>
        )}
      </Button>
    </form>
  );
}

function MfaStep({
  challenge,
  onBack,
  onDone,
  onError,
}: {
  challenge: LoginChallenge;
  onBack: () => void;
  onDone: () => void;
  onError: (m: string | null) => void;
}) {
  const verify = useVerifyMfa();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });

  const onSubmit = (values: CodeForm) => {
    onError(null);
    verify.mutate(
      { challenge_token: challenge.challenge_token, code: values.code },
      { onSuccess: onDone, onError: (e) => onError(errorMessage(e)) },
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      {challenge.mfa_enrolment_required ? (
        <div className="rounded-2xl border border-line bg-card p-4 shadow-card">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-logo-teal-wash text-logo-teal">
              <Smartphone className="h-[18px] w-[18px]" strokeWidth={1.8} />
            </span>
            <div className="text-xs text-ink-2">
              <p className="font-semibold text-ink">Add this account to your authenticator app</p>
              <p className="mt-1">Scan the QR code with Google Authenticator, 1Password or similar, then enter the code it shows.</p>
            </div>
          </div>
          <EnrolmentQr otpauthUri={challenge.otpauth_uri} />
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl border border-line bg-card p-4 text-xs text-ink-2 shadow-card">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-grove-wash text-grove">
            <ShieldCheck className="h-[18px] w-[18px]" strokeWidth={1.8} />
          </span>
          Open your authenticator app and enter the current code for AV Control Center.
        </div>
      )}

      <div>
        <label htmlFor="mfa-code" className="mb-1.5 block text-xs font-semibold text-ink-2">
          6-digit code
        </label>
        <div className="relative">
          <KeyRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="mfa-code"
            {...register('code')}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            autoFocus
            placeholder="123456"
            aria-invalid={!!errors.code}
            className={cn(fieldClass, 'pr-4 font-mono tracking-[0.3em]', errors.code && 'border-danger')}
          />
        </div>
        {errors.code && <p className="mt-1.5 text-xs font-medium text-danger">{errors.code.message}</p>}
      </div>

      <Button type="submit" disabled={verify.isPending} className="h-11 w-full">
        {verify.isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Verifying...</span>
          </>
        ) : (
          <span>{challenge.mfa_enrolment_required ? 'Verify and finish setup' : 'Verify and sign in'}</span>
        )}
      </Button>

      <button
        type="button"
        onClick={onBack}
        disabled={verify.isPending}
        className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover disabled:opacity-60"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        <span>Use a different account</span>
      </button>
    </form>
  );
}
