"use client"

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"

import ReauthDialog from "@/components/auth/ReauthDialog"
import { ApiError, clearSession, fetchMe, getToken, setReauthHandler, type Me } from "@/lib/api"

interface Session {
  me: Me
  signOut: () => void
}

const SessionContext = createContext<Session | null>(null)

/** The signed-in user and clinic. Only valid inside <AuthGate>. */
export function useSession(): Session {
  const session = useContext(SessionContext)
  if (!session) throw new Error("useSession must be used inside <AuthGate>")
  return session
}

/** Only a same-site path may follow the login page; anything else goes home. */
export function safeNext(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/"
  return value
}

function loginUrl(extra: string) {
  const here = `${window.location.pathname}${window.location.search}`
  return `/login?${extra}next=${encodeURIComponent(here)}`
}

type GateState =
  | { kind: "checking" }
  | { kind: "ready"; me: Me }
  | { kind: "error"; message: string }

/**
 * Keeps the posture tool behind a sign-in. No token goes to /login and
 * comes back to the same address afterwards (the CRM opens
 * /analyze?patient_id=...). While a session is open, a 401 from the posture
 * API opens a password dialog instead of leaving the page, so photos and
 * reviewed points survive an expired session.
 */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [state, setState] = useState<GateState>({ kind: "checking" })
  const [reauthOpen, setReauthOpen] = useState(false)
  const reauthResolve = useRef<((ok: boolean) => void) | null>(null)

  // Bumped by "Try again" to run the check once more.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!getToken()) {
      router.replace(loginUrl(""))
      return
    }
    let active = true
    fetchMe()
      .then((me) => {
        if (active) setState({ kind: "ready", me })
      })
      .catch((err) => {
        if (!active) return
        if (err instanceof ApiError && err.status === 401) {
          clearSession()
          router.replace(loginUrl("expired=1&"))
          return
        }
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Could not load your account.",
        })
      })
    return () => {
      active = false
    }
  }, [router, attempt])

  const retry = () => {
    setState({ kind: "checking" })
    setAttempt((n) => n + 1)
  }

  useEffect(() => {
    setReauthHandler(
      () =>
        new Promise<boolean>((resolve) => {
          reauthResolve.current = resolve
          setReauthOpen(true)
        }),
    )
    return () => setReauthHandler(null)
  }, [])

  const finishReauth = (ok: boolean) => {
    setReauthOpen(false)
    reauthResolve.current?.(ok)
    reauthResolve.current = null
  }

  const signOut = useCallback(() => {
    clearSession()
    router.replace("/login")
  }, [router])

  if (state.kind === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8F4EA] text-[14px] text-[#5D6380]">
        Loading...
      </div>
    )
  }

  if (state.kind === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8F4EA] px-4">
        <div className="w-full max-w-sm rounded-2xl border border-[#E3DCCB] bg-white p-6 text-center">
          <p role="alert" className="text-[14px] text-[#B4231B]">{state.message}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-4 h-10 rounded-xl bg-[#0B1238] px-4 text-[14px] font-semibold text-white"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const canRun = (state.me.capabilities?.["posture.create"] ?? "none") !== "none"

  return (
    <SessionContext.Provider value={{ me: state.me, signOut }}>
      {canRun ? (
        children
      ) : (
        <div className="flex min-h-screen items-center justify-center bg-[#F8F4EA] px-4">
          <div className="w-full max-w-md rounded-2xl border border-[#E3DCCB] bg-white p-6">
            <h1 className="font-display text-[20px] font-bold text-[#141A33]">No access to posture analysis</h1>
            <p className="mt-2 text-[14px] leading-relaxed text-[#454B66]">
              You are signed in to {state.me.clinic?.name ?? "this clinic"} as {state.me.user.email}, but your
              account is not allowed to run posture analyses. Ask your clinic admin to grant
              &ldquo;Run Posture Analysis&rdquo; in Permissions.
            </p>
            <button
              type="button"
              onClick={signOut}
              className="mt-5 h-10 rounded-xl border border-[#E3DCCB] px-4 text-[14px] font-semibold text-[#141A33]"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
      <ReauthDialog open={reauthOpen} email={state.me.user.email} onDone={finishReauth} />
    </SessionContext.Provider>
  )
}
