"use client"

import { useState } from "react"

import { login, setSession, tokenClinicId } from "@/lib/api"

/**
 * Asked when the session ends in the middle of an assessment. Signs the same
 * person back in to the same clinic, so the request that failed can be sent
 * again with nothing on the page lost.
 */
export default function ReauthDialog({
  open,
  email,
  onDone,
}: {
  open: boolean
  email: string
  onDone: (ok: boolean) => void
}) {
  // Mounted fresh each time it opens, so no password or error is carried over.
  return open ? <ReauthForm email={email} onDone={onDone} /> : null
}

function ReauthForm({ email, onDone }: { email: string; onDone: (ok: boolean) => void }) {
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) {
      setError("Enter your password.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      const token = await login(email, password, tokenClinicId() ?? undefined)
      setSession(token, email)
      onDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed. Please try again.")
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0B1238]/60 px-4">
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="reauth-title"
        onSubmit={submit}
        noValidate
        className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
      >
        <h2 id="reauth-title" className="font-display text-[19px] font-bold text-[#141A33]">
          Your session has ended
        </h2>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-[#454B66]">
          Enter your password to continue. Your photos and checked points are kept.
        </p>
        <p className="mt-4 text-[12px] font-medium text-[#5D6380]">Signed in as</p>
        <p className="truncate text-[14px] font-semibold text-[#141A33]">{email}</p>
        <label className="mt-4 block">
          <span className="mb-1.5 block text-[13px] font-medium text-[#454B66]">Password</span>
          <input
            autoFocus
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-11 w-full rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-3 text-[15px] text-[#141A33] outline-none focus:border-[#4E888F]"
          />
        </label>
        {error && (
          <p role="alert" className="mt-2 text-[12.5px] font-medium text-[#B4231B]">
            {error}
          </p>
        )}
        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => onDone(false)}
            disabled={busy}
            className="h-11 flex-1 rounded-xl border border-[#E3DCCB] text-[14px] font-semibold text-[#141A33] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="h-11 flex-1 rounded-xl bg-[#0B1238] text-[14px] font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Signing in..." : "Continue"}
          </button>
        </div>
      </form>
    </div>
  )
}
