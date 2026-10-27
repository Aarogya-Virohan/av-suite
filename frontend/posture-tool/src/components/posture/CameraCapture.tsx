"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import {
  MAX_TILT_DEG,
  biasFromReversal,
  isSteady,
  loadCalibration,
  mean,
  normalise,
  pitchFromGravity,
  platformSign,
  recent,
  rollFromGravity,
  rollUpsideDown,
  rotationSpeed,
  saveCalibration,
} from "@/lib/tilt"
import type { Calibration, CaptureLevel, Gravity, TiltSample } from "@/lib/tilt"

export type CaptureView = "front" | "side" | "back"

interface CameraCaptureProps {
  view: CaptureView
  label: string
  // level is null when the device could not report its tilt.
  onCapture: (file: File, previewUrl: string, level: CaptureLevel | null) => void
  onClose: () => void
}

// 27 October 2026. Until now the shutter stayed off until the phone was
// within 1.5 degrees of level in both directions (founders' guideline of
// 10 October). By hand that was close to impossible, the founders and Onkar
// both found it unusable, and a tripod is not always available. It was
// also less exact than it looked, because a phone accelerometer has a fixed
// offset of its own.
//
// Now the shutter only needs the phone steady and roughly upright (within
// MAX_TILT_DEG). The exact side tilt at the moment of capture travels with
// the photograph, minus this phone's own offset once it has been calibrated,
// and the backend turns the reviewed points back by it (level.py). Forward
// tilt within 10 degrees moves no graded angle by more than about 0.2.
//
// A device that cannot report its tilt (a laptop, or motion access refused)
// can still capture; its photographs carry no tilt and the report says the
// tilt was not measured.

type LevelStatus = "off" | "waiting" | "active" | "unavailable" | "denied"

// If no motion reading arrives within this time, the device has no sensor.
const LEVEL_TIMEOUT_MS = 1500
// After the tap, wait this long before looking for a steady moment, so the
// shake of the tap itself is not in the picture or the reading.
const TAP_SETTLE_MS = 300
// Give up looking for a steady moment after this long.
const CAPTURE_TIMEOUT_MS = 3000
// Readings kept, a little more than the steadiness window.
const SAMPLE_KEEP_MS = 1500
// Calibration: each position must hold still this long.
const CAL_HOLD_MS = 1200

// iOS only delivers motion events after a permission granted inside a user
// tap. The "Use camera" tap that opens this screen is that tap, so the
// slot calls this before opening the camera, and the level check then
// starts by itself. Android needs no permission and resolves at once.
//
// One request is shared: the camera screen asks again as it opens, and on
// iOS a second call made outside a tap, while the first prompt is still on
// screen, would be refused and wrongly show the level as denied. A refusal
// is not kept, so a later tap can ask again.
let motionPermission: Promise<boolean> | null = null

// The setup sheet opens on the first camera of a page visit, not on every
// one; "?" brings it back.
let setupSeenThisVisit = false
// "Later" on the calibration prompt holds for the rest of the page visit.
let calibrationDeferredThisVisit = false

export function requestMotionPermission(): Promise<boolean> {
  type MotionPermission = { requestPermission?: () => Promise<"granted" | "denied"> }
  if (typeof window === "undefined" || !("DeviceMotionEvent" in window)) {
    return Promise.resolve(false)
  }
  if (motionPermission) return motionPermission
  const api = DeviceMotionEvent as unknown as MotionPermission
  if (typeof api.requestPermission !== "function") {
    motionPermission = Promise.resolve(true)
    return motionPermission
  }
  const pending = api.requestPermission().then(
    (r) => r === "granted",
    () => false,
  )
  motionPermission = pending
  pending.then((ok) => {
    if (!ok && motionPermission === pending) motionPermission = null
  })
  return pending
}

const GUIDANCE: Record<CaptureView, string> = {
  front: "Patient faces the camera. Feet on the floor markers, arms relaxed at the sides, eyes level and looking straight ahead.",
  side: "Patient turns side-on. Arms hanging naturally, eyes level and looking straight ahead. Do not let them correct their posture.",
  back: "Patient faces away. Feet on the floor markers, arms relaxed at the sides.",
}

type CalStep = "intro" | "upright" | "flipped" | "done" | "failed"

export default function CameraCapture({
  view,
  label,
  onCapture,
  onClose,
}: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const [levelStatus, setLevelStatus] = useState<LevelStatus>("off")
  const motionHandlerRef = useRef<((e: DeviceMotionEvent) => void) | null>(null)
  const [layers, setLayers] = useState<GuideLayers>({
    lines: true,
    grid: true,
  })
  const [showSetup, setShowSetup] = useState(() => !setupSeenThisVisit)

  // Latest raw gravity, and recent upright readings (roll uncorrected).
  const gravityRef = useRef<Gravity | null>(null)
  const signRef = useRef<1 | -1 | null>(null)
  // The same, as state, for what the screen renders.
  const [sign, setSign] = useState<1 | -1 | null>(null)
  const samplesRef = useRef<TiltSample[]>([])
  // What the screen shows, refreshed from the samples a few times a second.
  const [view_, setView] = useState<{ roll: number; pitch: number; steady: boolean } | null>(null)

  const [calibration, setCalibration] = useState<Calibration | null>(null)
  const [calStep, setCalStep] = useState<CalStep | null>(null)
  const calFirstRef = useRef<number | null>(null)

  const [calDeferred, setCalDeferred] = useState(() => calibrationDeferredThisVisit)
  const [capturing, setCapturing] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    // Read after mount: localStorage is not there during the server render.
    const t = window.setTimeout(() => setCalibration(loadCalibration()), 0)
    return () => window.clearTimeout(t)
  }, [])

  // ---- camera ----
  useEffect(() => {
    let cancelled = false

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        })

        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }

        streamRef.current = stream

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          setReady(true)
        }
      } catch (e) {
        const name = e instanceof DOMException ? e.name : ""

        if (name === "NotAllowedError") {
          setError("Camera permission was denied. Allow camera access in your browser settings, or upload a photo instead.")
        } else if (name === "NotFoundError") {
          setError("No camera found on this device. Upload a photo instead.")
        } else {
          setError("Could not start the camera on this device. Upload a photo instead.")
        }
      }
    }

    start()

    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  // ---- back button ----
  // The camera is a state overlay, not a route, so Android's back button
  // would navigate off the site and close the whole capture. Push a
  // history entry on open and close on popstate instead.
  useEffect(() => {
    window.history.pushState({ cameraOpen: true }, "")

    const onPop = () => onClose()

    window.addEventListener("popstate", onPop)

    return () => {
      window.removeEventListener("popstate", onPop)
    }
  }, [onClose])

  // ---- motion ----
  // iOS requires an explicit user gesture before motion events are
  // delivered, so this is requested from a button rather than on mount.
  const enableLevel = useCallback(async () => {
    if (typeof window === "undefined" || !("DeviceMotionEvent" in window)) {
      setLevelStatus("unavailable")
      return
    }

    if (!(await requestMotionPermission())) {
      setLevelStatus("denied")
      return
    }

    setLevelStatus("waiting")
    let received = false

    const handler = (e: DeviceMotionEvent) => {
      const a = e.accelerationIncludingGravity
      if (!a || a.x === null || a.y === null || a.z === null) return
      received = true
      const g = { x: a.x, y: a.y, z: a.z }
      gravityRef.current = g

      // Only upright readings are kept for capture; the convention is fixed
      // from the first clearly upright one.
      if (Math.abs(g.y) > Math.hypot(g.x, g.z)) {
        if (signRef.current === null) {
          signRef.current = platformSign(g)
          setSign(signRef.current)
        }
        if (signRef.current === platformSign(g)) {
          const n = normalise(g, signRef.current)
          const now = performance.now()
          const samples = samplesRef.current
          samples.push({
            t: now,
            roll: rollFromGravity(n),
            pitch: pitchFromGravity(n),
            rate: rotationSpeed(e.rotationRate),
          })
          while (samples.length && now - samples[0].t > SAMPLE_KEEP_MS) samples.shift()
        }
      }
      setLevelStatus("active")
    }

    if (motionHandlerRef.current) {
      window.removeEventListener("devicemotion", motionHandlerRef.current)
    }
    motionHandlerRef.current = handler
    window.addEventListener("devicemotion", handler)

    window.setTimeout(() => {
      if (!received) setLevelStatus("unavailable")
    }, LEVEL_TIMEOUT_MS)
  }, [])

  // Starts by itself when the camera opens; no button. If iOS still refuses
  // (permission not granted from the tap), the screen offers one.
  useEffect(() => {
    // Started from a timer rather than in the effect body, so its state
    // updates happen in a callback and not during the commit.
    const start = window.setTimeout(() => void enableLevel(), 0)
    return () => {
      window.clearTimeout(start)
      if (motionHandlerRef.current) {
        window.removeEventListener("devicemotion", motionHandlerRef.current)
        motionHandlerRef.current = null
      }
    }
  }, [enableLevel])

  // The bubble and the shutter state, about ten times a second rather than
  // on every motion event.
  useEffect(() => {
    if (levelStatus !== "active") return
    const id = window.setInterval(() => {
      const now = performance.now()
      const w = recent(samplesRef.current, now, 200)
      if (!w.length) {
        setView(null)
        return
      }
      setView({
        roll: mean(w.map((s) => s.roll)),
        pitch: mean(w.map((s) => s.pitch)),
        steady: isSteady(samplesRef.current, now),
      })
    }, 100)
    return () => window.clearInterval(id)
  }, [levelStatus])

  const bias = calibration && calibration.sign === sign ? calibration.biasDeg : 0
  const calibrated = calibration !== null && calibration.sign === sign

  // ---- capture ----
  const grabFrame = useCallback(
    (level: CaptureLevel | null) => {
      const video = videoRef.current
      if (!video) return

      const canvas = document.createElement("canvas")
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

      // PNG, not JPEG, because JPEG is lossy at any quality setting and the
      // loss is large enough to move a grade. Measured 3 October 2026 on the
      // seven test subjects: re-encoding a front view once at quality 95
      // shifted knee deviation by 0.40 degrees on average and 1.19 at worst,
      // and changed the reported direction or severity on 4 of 14 legs.
      // PNG changed nothing at all. About 8.7 MB a photo against 1.4.
      canvas.toBlob(
        (blob) => {
          if (!blob) return

          const file = new File([blob], `posture-${view}-${Date.now()}.png`, {
            type: "image/png",
          })

          onCapture(file, URL.createObjectURL(blob), level)

          // Close after handing the file over. The camera modal pushed a
          // history entry when it opened, so step back through it rather
          // than calling onClose directly; otherwise the entry is left
          // behind and the next Android back press closes the site.
          window.history.back()
        },
        "image/png",
      )
    },
    [view, onCapture],
  )

  const capture = useCallback(() => {
    if (capturing) return
    setNotice(null)

    // No tilt reading on this device: take the photo as it is.
    if (levelStatus === "unavailable" || levelStatus === "denied") {
      grabFrame(null)
      return
    }

    setCapturing(true)
    const tapAt = performance.now()

    const poll = () => {
      const now = performance.now()
      if (now - tapAt > CAPTURE_TIMEOUT_MS) {
        setCapturing(false)
        setNotice("The phone did not stay still. Hold it steady and tap again.")
        return
      }
      // Only readings after the tap has settled count.
      const after = samplesRef.current.filter((s) => s.t >= tapAt + TAP_SETTLE_MS)
      if (now - tapAt >= TAP_SETTLE_MS && isSteady(after, now)) {
        const w = recent(after, now)
        const roll = mean(w.map((s) => s.roll)) - bias
        const pitch = mean(w.map((s) => s.pitch))
        if (Math.abs(roll) <= MAX_TILT_DEG && pitch <= MAX_TILT_DEG) {
          setCapturing(false)
          grabFrame({ degrees: Math.round(roll * 100) / 100, calibrated })
          return
        }
      }
      window.setTimeout(poll, 50)
    }
    window.setTimeout(poll, 50)
  }, [capturing, levelStatus, grabFrame, bias, calibrated])

  // ---- calibration ----
  // Reversal: the phone stands on its bottom edge, then upside down on its
  // top edge, on the same flat spot. See lib/tilt.ts.
  useEffect(() => {
    if (calStep !== "upright" && calStep !== "flipped") return
    const readings: { t: number; roll: number; g: Gravity }[] = []
    const id = window.setInterval(() => {
      const g = gravityRef.current
      const sign = signRef.current
      if (!g || sign === null) return
      const n = normalise(g, sign)
      const upright = calStep === "upright"
      // Wrong way up for this step: wait.
      if (upright ? n.y <= 0 : n.y >= 0) {
        readings.length = 0
        return
      }
      const now = performance.now()
      readings.push({ t: now, roll: upright ? rollFromGravity(n) : rollUpsideDown(n), g: n })
      while (readings.length && now - readings[0].t > CAL_HOLD_MS) readings.shift()
      const span = Math.max(...readings.map((r) => r.roll)) - Math.min(...readings.map((r) => r.roll))
      const held = readings.length >= 10 && now - readings[0].t >= CAL_HOLD_MS * 0.9
      // At rest on a table a phone's readings wander a few tenths of a degree
      // from sensor noise; being picked up or nudged moves them far more.
      if (span > 1.0) {
        // Moved: start this position again.
        readings.splice(0, readings.length - 1)
        return
      }
      if (!held) return
      const r = mean(readings.map((x) => x.roll))
      if (upright) {
        calFirstRef.current = r
        setCalStep("flipped")
      } else {
        const b = biasFromReversal(calFirstRef.current ?? r, r)
        if (Math.abs(b) > 10) {
          setCalStep("failed")
          return
        }
        const c: Calibration = { biasDeg: Math.round(b * 100) / 100, sign, at: new Date().toISOString() }
        saveCalibration(c)
        setCalibration(c)
        setCalStep("done")
      }
    }, 50)
    return () => window.clearInterval(id)
  }, [calStep])

  const tiltKnown = levelStatus === "active" && view_ !== null
  const correctedRoll = view_ ? view_.roll - bias : 0
  const withinRange = tiltKnown && Math.abs(correctedRoll) <= MAX_TILT_DEG && view_!.pitch <= MAX_TILT_DEG
  const canCapture =
    ready &&
    !capturing &&
    calStep === null &&
    (levelStatus === "unavailable" || levelStatus === "denied" || (withinRange && view_!.steady))

  const showCalPrompt =
    levelStatus === "active" && !showSetup && calStep === null && !calibrated && !calDeferred

  const guidesOn = layers.lines || layers.grid

  let hint: string
  if (capturing) hint = "Hold still..."
  else if (levelStatus === "unavailable") hint = "Tilt not measured on this device. Tap to capture"
  else if (levelStatus === "denied") hint = "Tilt not measured. Tap to capture"
  else if (!tiltKnown) hint = "Hold the phone upright"
  else if (!withinRange) hint = "Hold the phone upright"
  else if (!view_!.steady) hint = "Hold steady"
  else hint = "Tap to capture"

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black text-white">
      {/* Top bar, above the picture so it never covers the head guide line */}
      <div className="flex items-center justify-between gap-2 px-3 pb-2 pt-[max(10px,env(safe-area-inset-top))]">
        <button
          type="button"
          onClick={onClose}
          className="h-10 rounded-full bg-white/10 px-4 text-[14px] font-medium backdrop-blur-md"
        >
          Cancel
        </button>
        <span className="text-[15px] font-semibold">{label} view</span>
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setLayers({ lines: !guidesOn, grid: !guidesOn })}
            aria-pressed={guidesOn}
            className={`h-10 rounded-full px-3 text-[13px] font-medium backdrop-blur-md ${
              guidesOn ? "bg-white text-[#141A33]" : "bg-white/10 text-white"
            }`}
          >
            Guides
          </button>
          <button
            type="button"
            onClick={() => setShowSetup(true)}
            aria-label="Capture setup"
            className="h-10 w-10 rounded-full bg-white/10 text-[15px] font-semibold backdrop-blur-md"
          >
            ?
          </button>
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden">
        <video ref={videoRef} playsInline muted className="h-full w-full object-contain" />

        {ready && <SilhouetteGuide layers={layers} />}

        {showSetup && (
          <div className="absolute inset-0 z-10 flex items-end justify-center bg-black/80 p-4 sm:items-center">
            <div className="w-full max-w-sm space-y-4 rounded-2xl bg-[#0B1238] p-5">
              <h3 className="text-[17px] font-semibold">Before you capture</h3>
              <ul className="space-y-2.5 text-[14px] leading-snug text-white/80">
                <li>Hold the phone upright at about half the patient&apos;s height, or use a tripod if you have one. Small tilts are measured and corrected.</li>
                <li>Stand 1.5 to 3 m from the patient, in the same spot every visit.</li>
                <li>Patient on the floor marker, feet in the standard position.</li>
                <li>Clothing that shows the shoulders, hips, knees and ankles.</li>
                <li>Head and feet inside the guide lines. A cropped head or foot drops every millimetre measurement from the report.</li>
              </ul>
              <p className="text-[12px] leading-snug text-white/50">
                Keep the distance and height the same between visits. Changing them makes the measurements less comparable.
              </p>
              {levelStatus === "active" && (
                <button
                  type="button"
                  onClick={() => {
                    setupSeenThisVisit = true
                    setShowSetup(false)
                    setCalStep("intro")
                  }}
                  className="h-11 w-full rounded-xl bg-white/10 text-[14px] font-medium"
                >
                  {calibrated ? "Calibrate this phone again" : "Calibrate this phone"}
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  setupSeenThisVisit = true
                  setShowSetup(false)
                }}
                className="h-12 w-full rounded-xl bg-white text-[15px] font-medium text-[#141A33]"
              >
                Got it
              </button>
            </div>
          </div>
        )}

        {showCalPrompt && (
          <div className="absolute inset-x-3 top-3 z-10 rounded-2xl bg-[#0B1238]/95 p-4 backdrop-blur-md">
            <p className="text-[14px] font-semibold">Calibrate this phone once</p>
            <p className="mt-1 text-[13px] leading-snug text-white/70">
              Takes about 20 seconds on any table. It removes this phone&apos;s own tilt error so the correction is exact.
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => setCalStep("intro")}
                className="h-10 flex-1 rounded-xl bg-white text-[14px] font-medium text-[#141A33]"
              >
                Calibrate
              </button>
              <button
                type="button"
                onClick={() => {
                  calibrationDeferredThisVisit = true
                  setCalDeferred(true)
                }}
                className="h-10 flex-1 rounded-xl bg-white/10 text-[14px] font-medium"
              >
                Later
              </button>
            </div>
          </div>
        )}

        {calStep !== null && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/90 p-6">
            <div className="w-full max-w-sm space-y-4 text-center">
              <CalFigure flipped={calStep === "flipped"} />
              {calStep === "intro" && (
                <>
                  <h3 className="text-[17px] font-semibold">Calibrate this phone</h3>
                  <p className="text-[14px] leading-snug text-white/75">
                    Stand the phone upright on its bottom edge on a table, screen towards you, leaning against something so it stays still. The table does not need to be level.
                  </p>
                  <button
                    type="button"
                    onClick={() => setCalStep("upright")}
                    className="h-12 w-full rounded-xl bg-white text-[15px] font-medium text-[#141A33]"
                  >
                    Start
                  </button>
                </>
              )}
              {calStep === "upright" && (
                <p className="text-[15px] leading-snug">Phone upright on its bottom edge. Let go and keep it still...</p>
              )}
              {calStep === "flipped" && (
                <p className="text-[15px] leading-snug">
                  Now turn it upside down, standing on its top edge, in the same spot. Let go and keep it still...
                </p>
              )}
              {calStep === "done" && (
                <>
                  <p className="text-[15px] font-semibold text-[#3FB68B]">Calibrated</p>
                  <p className="text-[13px] text-white/60">This phone remembers it in this browser.</p>
                  <button
                    type="button"
                    onClick={() => setCalStep(null)}
                    className="h-12 w-full rounded-xl bg-white text-[15px] font-medium text-[#141A33]"
                  >
                    Continue
                  </button>
                </>
              )}
              {calStep === "failed" && (
                <>
                  <p className="text-[15px] leading-snug text-[#F2B8B5]">
                    The two readings did not agree. Use the same spot on the table for both and try again.
                  </p>
                  <button
                    type="button"
                    onClick={() => setCalStep("upright")}
                    className="h-12 w-full rounded-xl bg-white text-[15px] font-medium text-[#141A33]"
                  >
                    Try again
                  </button>
                </>
              )}
              {calStep !== "done" && (
                <button
                  type="button"
                  onClick={() => setCalStep(null)}
                  className="h-10 w-full text-[13px] text-white/60"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 p-8">
            <p className="max-w-xs text-center text-[15px] leading-relaxed">{error}</p>
          </div>
        )}
      </div>

      {/* Bottom panel */}
      <div className="space-y-3 bg-black px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3">
        <p className="text-center text-[13px] leading-snug text-white/60">{GUIDANCE[view]}</p>

        {levelStatus === "denied" && (
          <div className="text-center">
            <button
              type="button"
              onClick={() => void enableLevel()}
              className="h-9 rounded-full bg-white/10 px-4 text-[13px] font-medium"
            >
              Allow motion access to correct tilt
            </button>
          </div>
        )}

        <div className="flex items-center justify-center gap-6">
          {tiltKnown ? (
            <Bubble roll={correctedRoll} ok={withinRange && view_!.steady} />
          ) : (
            <div className="h-14 w-14" />
          )}

          <button
            type="button"
            onClick={capture}
            disabled={!canCapture}
            aria-label="Capture"
            className={`flex h-[76px] w-[76px] items-center justify-center rounded-full border-4 transition ${
              canCapture ? "border-[#3FB68B]" : "border-white/25"
            }`}
          >
            <span
              className={`h-[60px] w-[60px] rounded-full transition ${
                canCapture ? "bg-white" : "bg-white/20"
              }`}
            />
          </button>

          <div className="h-14 w-14" />
        </div>

        <p
          className={`text-center text-[13px] font-medium ${
            notice ? "text-[#F2B8B5]" : canCapture ? "text-[#3FB68B]" : "text-white/60"
          }`}
          aria-live="polite"
        >
          {notice ?? hint}
        </p>
      </div>
    </div>
  )
}

// A level bubble: the dot sits in the middle when the phone is upright and
// moves the way its top leans, reaching the edge at MAX_TILT_DEG. Anywhere
// inside is fine, because the side tilt is corrected afterwards; the bubble
// shows which way to straighten, it does not have to be centred. Forward
// lean has no sign that holds on every phone, so it is not drawn; when it is
// out of range the dot stays white and the hint says to hold upright.
function Bubble({ roll, ok }: { roll: number; ok: boolean }) {
  const r = 22
  const clamp = (v: number) => Math.max(-1, Math.min(1, v / MAX_TILT_DEG))
  const dx = clamp(-roll) * r
  const dy = 0
  return (
    <svg viewBox="-28 -28 56 56" className="h-14 w-14" aria-hidden>
      <circle r={r + 4} fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.35)" strokeWidth="1" />
      <line x1={-6} y1={0} x2={6} y2={0} stroke="rgba(255,255,255,0.4)" strokeWidth="1" />
      <line x1={0} y1={-6} x2={0} y2={6} stroke="rgba(255,255,255,0.4)" strokeWidth="1" />
      <circle cx={dx} cy={dy} r={6} fill={ok ? "#3FB68B" : "rgba(255,255,255,0.7)"} />
    </svg>
  )
}

function CalFigure({ flipped }: { flipped: boolean }) {
  return (
    <svg viewBox="0 0 120 90" className="mx-auto h-24 w-32" aria-hidden>
      <line x1="10" y1="80" x2="110" y2="80" stroke="rgba(255,255,255,0.5)" strokeWidth="2" />
      <g transform={flipped ? "rotate(180 60 50)" : undefined}>
        <rect x="45" y="20" width="30" height="60" rx="5" fill="none" stroke="white" strokeWidth="2" />
        <circle cx="60" cy="28" r="2" fill="white" />
      </g>
    </svg>
  )
}

type GuideLayers = {
  lines: boolean
  grid: boolean
}

// Frame bounds in viewBox units (0-200 tall). Deliberately not a body
// outline: with the camera on a tripod at a fixed distance, the operator
// must not move the patient to fit a shape. Doing that puts a short and a
// tall patient at different distances and therefore under different
// perspective distortion, which is what breaks visit-to-visit comparison.
// The one thing that must hold in every frame is that the whole body is
// inside it, because the pixel-to-millimetre calibration is measured
// nose-to-ankle and drops every millimetre parameter if either end is
// cropped.
const FRAME = { head: 12, feet: 188 }

function SilhouetteGuide({ layers }: { layers: GuideLayers }) {
  return (
    <>
    {layers.lines && (
      <>
        <span
          className="pointer-events-none absolute left-3 text-[11px] font-medium tracking-wide text-white"
          style={{ top: `${(FRAME.head / 200) * 100}%`, transform: "translateY(-135%)", textShadow: "0 0 3px rgba(0,0,0,0.9)" }}
        >
          Top of head inside this line
        </span>
        <span
          className="pointer-events-none absolute left-3 text-[11px] font-medium tracking-wide text-white"
          style={{ top: `${(FRAME.feet / 200) * 100}%`, transform: "translateY(35%)", textShadow: "0 0 3px rgba(0,0,0,0.9)" }}
        >
          Feet inside this line
        </span>
      </>
    )}
    <svg
      viewBox="0 0 100 200"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      {layers.grid && (
        <g>
          {Array.from({ length: 19 }, (_, i) => (i + 1) * 10).map((y) => (
            <line key={`h${y}`} x1="0" y1={y} x2="100" y2={y} stroke="rgba(255,255,255,0.22)" strokeWidth="0.25" />
          ))}
          {Array.from({ length: 9 }, (_, i) => (i + 1) * 10).map((x) => (
            <line key={`v${x}`} x1={x} y1="0" x2={x} y2="200" stroke="rgba(255,255,255,0.22)" strokeWidth="0.25" />
          ))}
        </g>
      )}

      {layers.lines && (
        <g>
          <line x1="50" y1="0" x2="50" y2="200" stroke="rgba(0,0,0,0.5)" strokeWidth="1.1" />
          <line x1="50" y1="0" x2="50" y2="200" stroke="rgba(255,255,255,0.75)" strokeWidth="0.4" strokeDasharray="3 2.5" />

          {[
            { y: FRAME.head, label: "Top of head inside this line" },
            { y: FRAME.feet, label: "Feet inside this line" },
          ].map(({ y, label }) => (
            <g key={label}>
              <line x1="0" y1={y} x2="100" y2={y} stroke="rgba(0,0,0,0.5)" strokeWidth="1.4" />
              <line x1="0" y1={y} x2="100" y2={y} stroke="rgba(255,255,255,0.85)" strokeWidth="0.5" strokeDasharray="4 3" />
            </g>
          ))}
        </g>
      )}
    </svg>
    </>
  )
}
