"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"

import { safeNext } from "@/components/auth/AuthGate"
import { ApiError, getToken, login, setSession, type WorkspaceOption } from "@/lib/api"

// Same sign-in as the CRM and the Exercise Library: one AV Suite account,
// and a clinic picker when the account belongs to more than one clinic.

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  therapist: "Therapist",
  front_desk: "Front desk",
}

const INPUT =
  "h-11 w-full rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[15px] text-[#141A33] outline-none transition placeholder:text-[#8B90A8] focus:border-[#4E888F]"

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const next = safeNext(params.get("next"))
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(
    params.get("expired") ? "Your session has ended. Please sign in again." : null,
  )
  const [busy, setBusy] = useState(false)
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[] | null>(null)
  const [pendingClinicId, setPendingClinicId] = useState<string | null>(null)

  // Already signed in: straight on.
  useEffect(() => {
    if (getToken()) router.replace(next)
  }, [router, next])

  async function signIn(clinicId?: string) {
    setError(null)
    try {
      const token = await login(email.trim(), password, clinicId)
      setSession(token, email.trim())
      router.replace(next)
    } catch (err) {
      if (err instanceof ApiError && err.code === "WORKSPACE_SELECTION_REQUIRED" && err.workspaces?.length) {
        setWorkspaces(err.workspaces)
        return
      }
      setError(err instanceof Error ? err.message : "Sign in failed. Please try again.")
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError("Enter your email and password.")
      return
    }
    setBusy(true)
    await signIn()
    setBusy(false)
  }

  const pickWorkspace = async (clinicId: string) => {
    setPendingClinicId(clinicId)
    await signIn(clinicId)
    setPendingClinicId(null)
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#F8F4EA]">
      <header className="bg-[linear-gradient(115deg,#0B1238_0%,#121F4A_60%,#1B4A54_100%)] text-white">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-4 px-4 py-3.5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/av_logo_wordmark_white.png" alt="Aarogya Virohan" className="h-6 w-auto" />
          <span className="rounded-full bg-[#C1FF72] px-2.5 py-0.5 text-[11.5px] font-bold text-[#0B1238]">
            Posture Tool
          </span>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm rounded-2xl border border-[#E3DCCB] bg-white p-6 sm:p-8">
          <h1 className="font-display text-[26px] font-extrabold tracking-tight text-[#141A33]">Sign in</h1>
          <p className="mt-1 text-[14px] text-[#5D6380]">Use your AV Suite account.</p>

          {error && (
            <p
              role="alert"
              className="mt-5 rounded-xl border border-[#B4231B]/20 bg-[#FDECEA] px-3.5 py-3 text-[13.5px] font-medium text-[#B4231B]"
            >
              {error}
            </p>
          )}

          {workspaces ? (
            <div className="mt-6 space-y-4">
              <div>
                <p className="text-[14px] font-semibold text-[#141A33]">Choose a clinic</p>
                <p className="mt-1 text-[12.5px] text-[#5D6380]">This account belongs to more than one clinic.</p>
              </div>
              <ul className="space-y-2">
                {workspaces.map((w) => (
                  <li key={w.clinic_id}>
                    <button
                      type="button"
                      onClick={() => pickWorkspace(w.clinic_id)}
                      disabled={pendingClinicId !== null}
                      className="flex w-full items-center justify-between gap-3 rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-4 py-3 text-left transition hover:border-[#4E888F] disabled:opacity-60"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-[14px] font-semibold text-[#141A33]">{w.name}</span>
                        {w.role && (
                          <span className="block text-[12px] text-[#5D6380]">{ROLE_LABEL[w.role] ?? w.role}</span>
                        )}
                      </span>
                      <span aria-hidden="true" className="text-[#5D6380]">
                        {pendingClinicId === w.clinic_id ? "..." : "›"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => {
                  setWorkspaces(null)
                  setError(null)
                }}
                disabled={pendingClinicId !== null}
                className="text-[13px] font-semibold text-[#4E888F] disabled:opacity-60"
              >
                Use a different account
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6 space-y-5" noValidate>
              <label className="block">
                <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">Email</span>
                <input
                  type="email"
                  autoComplete="email"
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@clinic.com"
                  className={INPUT}
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">Password</span>
                <span className="relative block">
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                    className={`${INPUT} pr-16`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[12.5px] font-semibold text-[#4E888F]"
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </span>
              </label>
              <button
                type="submit"
                disabled={busy}
                className="h-11 w-full rounded-xl bg-[#0B1238] text-[14px] font-semibold text-white transition disabled:opacity-70"
              >
                {busy ? "Signing in..." : "Sign in"}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
