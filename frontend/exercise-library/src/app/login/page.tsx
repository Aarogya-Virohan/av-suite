"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  Check,
  ChevronRight,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  Mail,
} from "lucide-react";
import { ApiError, getToken, login, setSession, type WorkspaceOption } from "@/lib/api";
import { cn } from "@/lib/utils";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  therapist: "Therapist",
  front_desk: "Front desk",
};

const fieldClass =
  "h-11 w-full rounded-[10px] border border-line bg-card pl-10 text-sm text-ink placeholder:text-[#767b93] transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(
    params.get("expired") ? "Your session has ended. Please sign in again." : null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[] | null>(null);
  const [pendingClinicId, setPendingClinicId] = useState<string | null>(null);

  // Already signed in: straight to the library.
  useEffect(() => {
    if (getToken()) router.replace("/");
  }, [router]);

  async function signIn(clinicId?: string) {
    setError(null);
    try {
      const token = await login(email.trim(), password, clinicId);
      setSession(token, email.trim());
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.code === "WORKSPACE_SELECTION_REQUIRED" && err.workspaces?.length) {
        setWorkspaces(err.workspaces);
        return;
      }
      setError(err instanceof Error ? err.message : "Sign in failed. Please try again.");
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setIsLoading(true);
    await signIn();
    setIsLoading(false);
  };

  const pickWorkspace = async (clinicId: string) => {
    setPendingClinicId(clinicId);
    await signIn(clinicId);
    setPendingClinicId(null);
  };

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden bg-[radial-gradient(90%_70%_at_0%_100%,rgba(27,74,84,0.95)_0%,rgba(27,74,84,0)_60%),linear-gradient(160deg,#0b1238_0%,#111c4a_55%,#0b1238_100%)] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gradient-to-br from-fresh to-[#0b665a] opacity-30 blur-2xl"
        />
        <div className="relative flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center overflow-hidden rounded-[13px] bg-white p-1.5 shadow-[0_0_0_2px_rgba(78,136,143,0.5)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
          </span>
          <div>
            <p className="font-display text-lg font-bold tracking-tight">AV Suite</p>
            <p className="text-xs text-[#aab2d6]">Exercise Library</p>
          </div>
        </div>

        <div className="relative max-w-md space-y-6">
          <h2 className="font-display text-[34px] font-bold leading-tight tracking-tight">
            Home exercise programmes, <span className="text-lime">ready in minutes.</span>
          </h2>
          <ul className="space-y-3 text-sm text-[#c3c9e6]">
            {[
              "Find exercises by name or body part",
              "Set sets, reps, hold and frequency",
              "Hand the patient a clean, branded PDF",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-lime/15">
                  <Check className="h-3.5 w-3.5 text-lime" />
                </span>
                {item}
              </li>
            ))}
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
            <p className="mt-1 text-sm text-muted-foreground">Sign in to the Exercise Library</p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2 rounded-[10px] border border-danger/20 bg-danger-wash px-3.5 py-3 text-sm font-medium text-danger"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {workspaces ? (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold text-ink">Choose a workspace</p>
                <p className="mt-1 text-xs text-muted-foreground">This account belongs to more than one clinic.</p>
              </div>
              <ul className="space-y-2">
                {workspaces.map((w) => (
                  <li key={w.clinic_id}>
                    <button
                      type="button"
                      onClick={() => pickWorkspace(w.clinic_id)}
                      disabled={pendingClinicId !== null}
                      className="flex w-full cursor-pointer items-center gap-3 rounded-[10px] border border-line bg-card px-4 py-3 text-left transition-colors hover:border-grove focus-visible:border-grove focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/15 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-grove/10 text-grove">
                        <Building2 className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-ink">{w.name}</span>
                        {w.role && (
                          <span className="block text-xs text-muted-foreground">{ROLE_LABEL[w.role] ?? w.role}</span>
                        )}
                      </span>
                      {pendingClinicId === w.clinic_id ? (
                        <Loader2 className="h-4 w-4 animate-spin text-grove" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-[#767b93]" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => {
                  setWorkspaces(null);
                  setError(null);
                }}
                disabled={pendingClinicId !== null}
                className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover disabled:opacity-60"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Use a different account
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <div>
                <label htmlFor="login-email" className="mb-1.5 block text-xs font-semibold text-ink-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767b93]" />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    autoFocus
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@clinic.com"
                    className={cn(fieldClass, "pr-4")}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="login-password" className="mb-1.5 block text-xs font-semibold text-ink-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767b93]" />
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                    className={cn(fieldClass, "pr-11")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-[#767b93] transition-colors hover:text-ink"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="flex h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-grove text-sm font-semibold text-white shadow-primary transition-colors hover:bg-grove-hover disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
