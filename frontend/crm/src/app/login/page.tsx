'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useAuthStore } from '../../store';
import { setStoredToken, getStoredToken, isTokenExpired } from '../../lib/auth';
import { apiClient } from '../../lib/api-client';
import { Check, Lock, Mail, Loader2, Eye, EyeOff } from 'lucide-react';
import { Button } from '../../components/ui/brand';
import { cn } from '../../lib/cn';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (token && !isTokenExpired(token)) {
      router.replace('/dashboard');
      return;
    }
    setIsCheckingAuth(false);
  }, [router]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true);
    try {
      // Direct POST to /auth/login sending plaintext credentials matching backend verification
      const res = await apiClient.post('/auth/login', {
        email: data.email.trim(),
        password: data.password,
      });

      const token = res.data?.access_token || res.data?.data?.access_token;
      if (!token) {
        throw new Error('Invalid authentication response from server.');
      }

      setStoredToken(token);
      setToken(token);
      await useAuthStore.getState().fetchMe();
      toast.success('Successfully logged in');
      router.replace('/dashboard');
    } catch (err: unknown) {
      console.error('Login error:', err);
      const errorMessage =
        err instanceof Error ? err.message : 'Login failed. Please check your credentials.';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (isCheckingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-midnight">
        <div className="flex items-center gap-3 text-lime">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="text-sm font-medium">Verifying session...</span>
        </div>
      </div>
    );
  }

  const fieldClass =
    'h-11 w-full rounded-[10px] border border-line bg-card pl-10 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 dark:border-slate-700 dark:bg-slate-900 dark:text-white';

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Brand panel */}
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
            <p className="text-xs text-[#aab2d6]">Clinic CRM</p>
          </div>
        </div>

        <div className="relative max-w-md space-y-6">
          <h2 className="font-display text-[34px] font-bold leading-tight tracking-tight">
            Run your physiotherapy clinic <span className="text-lime">in one place.</span>
          </h2>
          <ul className="space-y-3 text-sm text-[#c3c9e6]">
            {['Patients, treatments and SOAP notes', 'Appointments and online booking', 'Billing, payments and analytics'].map(
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

      {/* Form */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <span className="mb-5 grid h-11 w-11 place-items-center overflow-hidden rounded-xl bg-white p-1.5 shadow-card lg:hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
            </span>
            <h1 className="font-display text-[28px] font-bold tracking-tight text-ink">Welcome back</h1>
            <p className="mt-1 text-sm text-muted">Sign in to access your clinic portal</p>
          </div>

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
                  autoComplete="email"
                  placeholder="you@clinic.com"
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

            <Button type="submit" disabled={isLoading} className="h-11 w-full">
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In to Dashboard</span>
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
