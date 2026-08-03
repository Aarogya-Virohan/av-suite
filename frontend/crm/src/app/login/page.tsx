'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Activity, AlertCircle, Loader2, Lock, Mail } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/features/auth/auth.api';
import { getAuthSession, saveAuthSession } from '@/features/auth/auth.storage';

const getSafeNextPath = (nextPath: string | null): string => {
  if (!nextPath || !nextPath.startsWith('/') || nextPath.startsWith('//')) {
    return '/';
  }

  if (nextPath.startsWith('/login')) {
    return '/';
  }

  return nextPath;
};

const getRequestedNextPath = (): string => {
  if (typeof window === 'undefined') {
    return '/';
  }

  return getSafeNextPath(new URLSearchParams(window.location.search).get('next'));
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (getAuthSession()) {
      router.replace(getRequestedNextPath());
    }
  }, [router]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedEmail || !password) {
      setError('Enter your clinic email and password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await authApi.login({
        email: trimmedEmail,
        password,
      });
      const session = saveAuthSession(response.access_token, trimmedEmail);

      if (!session) {
        throw new Error('The login token is missing required clinic or role claims.');
      }

      toast.success('Signed in successfully.');
      router.replace(getRequestedNextPath());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to sign in.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(420px,520px)]">
        <section className="hidden bg-[var(--sidebar-bg)] px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
              <Activity className="h-5 w-5 text-teal-200" />
            </span>
            <div>
              <p className="text-sm font-bold uppercase tracking-widest text-white/60">AV Suite</p>
              <h1 className="text-2xl font-extrabold">Aarogya CRM</h1>
            </div>
          </div>

          <div className="max-w-xl space-y-6">
            <p className="text-sm font-bold uppercase tracking-widest text-teal-200">Clinic access</p>
            <h2 className="text-5xl font-black leading-tight">
              Sign in to your secure clinical workspace.
            </h2>
            <p className="max-w-lg text-base leading-7 text-white/70">
              Your clinic and role are resolved from the signed access token after authentication.
              Tenant access is enforced by the API on every request.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs text-white/65">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="font-bold text-white">JWT</p>
              <p className="mt-1">Bearer auth</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="font-bold text-white">Clinic</p>
              <p className="mt-1">Claim scoped</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="font-bold text-white">Role</p>
              <p className="mt-1">API enforced</p>
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-4 py-10 sm:px-6">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--navy)] text-white">
                <Activity className="h-6 w-6" />
              </div>
              <h1 className="text-2xl font-extrabold">Aarogya CRM</h1>
              <p className="mt-2 text-sm text-[var(--text-light)]">Sign in to continue.</p>
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--card-bg)] p-6 shadow-sm sm:p-8">
              <div className="mb-6">
                <h2 className="text-xl font-extrabold">Welcome back</h2>
                <p className="mt-1 text-sm text-[var(--text-light)]">
                  Use your clinic account credentials.
                </p>
              </div>

              {error && (
                <div className="mb-5 flex gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>{error}</p>
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[var(--text-light)]">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-light)]" />
                    <input
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] py-3 pl-10 pr-3 text-sm font-medium text-[var(--text)] outline-none transition focus:border-[var(--teal)] focus:ring-2 focus:ring-[var(--teal-glow)]"
                      placeholder="name@clinic.com"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[var(--text-light)]">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-light)]" />
                    <input
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] py-3 pl-10 pr-3 text-sm font-medium text-[var(--text)] outline-none transition focus:border-[var(--teal)] focus:ring-2 focus:ring-[var(--teal-glow)]"
                      placeholder="Enter password"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--teal)] px-4 py-3 text-sm font-bold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  {isLoading ? 'Signing in...' : 'Sign in'}
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
