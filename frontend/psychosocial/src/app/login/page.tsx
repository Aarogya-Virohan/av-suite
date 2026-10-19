'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, Building2, Check, ChevronRight, Eye, EyeOff, Loader2, Lock, Mail } from 'lucide-react';
import { API_URL } from '@/lib/api';
import { setStoredToken } from '@/lib/auth';
import { useTokenStatus } from '@/lib/use-token';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/brand';

interface Workspace {
  clinic_id: string;
  name: string;
  role: string;
}

const ROLE_LABEL: Record<string, string> = { admin: 'Admin', therapist: 'Therapist', front_desk: 'Front Desk' };

const fieldClass =
  'h-11 w-full rounded-[10px] border border-line bg-card pl-10 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15';

export default function LoginPage() {
  const router = useRouter();
  const tokenStatus = useTokenStatus();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [pendingClinic, setPendingClinic] = useState<string | null>(null);

  useEffect(() => {
    if (tokenStatus === 'valid') router.replace('/sessions');
  }, [tokenStatus, router]);

  async function signIn(clinicId?: string) {
    const res = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password, ...(clinicId ? { clinic_id: clinicId } : {}) }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = body?.detail;
      if (detail && typeof detail === 'object' && detail.code === 'WORKSPACE_SELECTION_REQUIRED' && Array.isArray(detail.workspaces)) {
        setWorkspaces(detail.workspaces as Workspace[]);
        return;
      }
      const message =
        typeof detail === 'string'
          ? detail
          : detail?.message || body?.meta?.error?.message || 'Sign in failed. Check your email and password.';
      throw new Error(message);
    }
    const token = body?.data?.access_token;
    if (!token) throw new Error('The server did not return a session. Please try again.');
    setStoredToken(token);
    router.replace('/sessions');
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setError('Enter a valid email address.');
      return;
    }
    if (!password) {
      setError('Enter your password.');
      return;
    }
    setBusy(true);
    try {
      await signIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed.');
    } finally {
      setBusy(false);
    }
  }

  async function choose(clinicId: string) {
    setPendingClinic(clinicId);
    setError(null);
    try {
      await signIn(clinicId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open this workspace.');
    } finally {
      setPendingClinic(null);
    }
  }

  if (tokenStatus !== 'missing') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-midnight">
        <Loader2 className="h-6 w-6 animate-spin text-lime" aria-label="Checking session" />
      </div>
    );
  }

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
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
            <p className="text-xs text-[#aab2d6]">Psycho-social screening</p>
          </div>
        </div>
        <div className="relative max-w-md space-y-6">
          <h2 className="font-display text-[34px] font-bold leading-tight tracking-tight">
            See the whole patient, <span className="text-lime">not just the joint.</span>
          </h2>
          <ul className="space-y-3 text-sm text-[#c3c9e6]">
            {['PHQ-9, GAD-7 and DASS-21, scored to published norms', 'Patients answer on their phone, one question at a time', 'Referral flags and history in one view'].map(
              (item) => (
                <li key={item} className="flex items-center gap-3">
                  <span className="grid h-6 w-6 place-items-center rounded-full bg-lime/15">
                    <Check className="h-3.5 w-3.5 text-lime" />
                  </span>
                  {item}
                </li>
              ),
            )}
          </ul>
        </div>
        <p className="relative text-xs text-[#7f88b3]">Aarogya Virohan · AV Suite</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <span className="mb-5 grid h-11 w-11 place-items-center overflow-hidden rounded-xl bg-white p-1.5 shadow-card lg:hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
            </span>
            <h1 className="font-display text-[28px] font-bold tracking-tight text-ink">Welcome back</h1>
            <p className="mt-1 text-sm text-muted">Sign in with your AV Suite clinic account</p>
          </div>

          {error ? (
            <p role="alert" className="mb-4 rounded-[10px] border border-danger/30 bg-danger-wash px-3 py-2.5 text-sm font-medium text-danger">
              {error}
            </p>
          ) : null}

          {workspaces ? (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold text-ink">Choose a workspace</p>
                <p className="mt-1 text-xs text-muted">This account belongs to more than one clinic.</p>
              </div>
              <ul className="space-y-2">
                {workspaces.map((w) => (
                  <li key={w.clinic_id}>
                    <button
                      type="button"
                      onClick={() => choose(w.clinic_id)}
                      disabled={pendingClinic !== null}
                      className="flex w-full cursor-pointer items-center gap-3 rounded-[10px] border border-line bg-card px-4 py-3 text-left transition-colors hover:border-grove disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-grove/10 text-grove">
                        <Building2 className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-ink">{w.name}</span>
                        <span className="block text-xs text-muted">{ROLE_LABEL[w.role] ?? w.role}</span>
                      </span>
                      {pendingClinic === w.clinic_id ? (
                        <Loader2 className="h-4 w-4 animate-spin text-grove" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => setWorkspaces(null)}
                className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Use a different account
              </button>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-5" noValidate>
              <div>
                <label htmlFor="email" className="mb-1.5 block text-xs font-semibold text-ink-2">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@clinic.com"
                    className={cn(fieldClass, 'pr-4')}
                  />
                </div>
              </div>
              <div>
                <label htmlFor="password" className="mb-1.5 block text-xs font-semibold text-ink-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className={cn(fieldClass, 'pr-11')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 cursor-pointer place-items-center text-slate-400 hover:text-ink"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <Button type="submit" disabled={busy} className="h-11 w-full">
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
