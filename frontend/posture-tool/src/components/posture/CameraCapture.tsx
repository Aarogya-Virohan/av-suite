"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type CaptureView = "front" | "side" | "back"

interface CameraCaptureProps {
  view: CaptureView
  label: string
  onCapture: (file: File, previewUrl: string) => void
  onClose: () => void
}

// Founders' guidelines, 10 October 2026, given three times: the capture
// button stays disabled until the phone is within 1.5 degrees of vertical
// in both pitch (leaning toward or away from the patient) and roll
// (turned sideways, which tilts the horizon). Roll is the one that makes
// one shoulder or one hip look higher than the other, and the previous
// check did not read it at all: it read pitch only, and only warned, at
// 3 and 10 degrees.
//
// A device that cannot report its tilt (a laptop, or permission refused)
// cannot capture. The upload path stays open for it, and an uploaded photo
// is already marked on the PDF as not checked against the protocol.
const LEVEL_LIMIT_DEG = 1.5
// Readings are smoothed so the button does not flicker on hand tremor.
const LEVEL_SMOOTHING = 0.2
// If no motion reading arrives within this time, the device has no sensor.
const LEVEL_TIMEOUT_MS = 1500

type LevelStatus = "off" | "waiting" | "active" | "unavailable" | "denied"

// Pitch and roll from the gravity vector, in degrees, both 0 when the
// phone stands upright in portrait. Taken from gravity rather than from
// deviceorientation's beta and gamma, which suffer gimbal lock exactly at
// upright (beta 90), where gamma stops meaning sideways tilt. Only the
// size is used: iOS and Android report gravity with opposite signs, so a
// direction would point the wrong way on one of them.
function levelFromGravity(x: number, y: number, z: number) {
  const deg = (r: number) => (r * 180) / Math.PI
  return {
    roll: Math.abs(deg(Math.atan2(x, Math.hypot(y, z)))),
    pitch: Math.abs(deg(Math.atan2(z, Math.hypot(x, y)))),
  }
}

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
  const [level, setLevel] = useState<{ roll: number; pitch: number } | null>(null)
  const [levelStatus, setLevelStatus] = useState<LevelStatus>("off")
  const motionHandlerRef = useRef<((e: DeviceMotionEvent) => void) | null>(null)
  const [layers, setLayers] = useState<GuideLayers>({
    lines: true,
    grid: true,
  })
  const [showSetup, setShowSetup] = useState(() => !setupSeenThisVisit)

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

  // ---- level ----
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
      const g = e.accelerationIncludingGravity
      if (!g || g.x === null || g.y === null || g.z === null) return
      received = true
      const next = levelFromGravity(g.x, g.y, g.z)
      setLevel((prev) =>
        prev
          ? {
              roll: prev.roll + LEVEL_SMOOTHING * (next.roll - prev.roll),
              pitch: prev.pitch + LEVEL_SMOOTHING * (next.pitch - prev.pitch),
            }
          : next,
      )
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
  // The old listener was never removed; this one is, when the camera closes.
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

  // ---- capture ----
  const capture = useCallback(() => {
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
    // and changed the reported direction or severity on 4 of 14 legs. One
    // leg went from 0.356 to 1.358 degrees and flipped from neutral to
    // varus. Quality 100 was no better, 3 of 14, for twice the file size.
    // PNG changed nothing at all, 0 of 14, 0.000 degrees.
    //
    // The cost is size: roughly 8.7 MB a photo against 1.4, so about 26 MB
    // for the three views instead of 4.3. That is a slower upload on a
    // clinic connection, and it is the right trade, because the whole point
    // of capturing in-app rather than accepting a forwarded photo is that
    // we control what reaches the model.
    canvas.toBlob(
      (blob) => {
        if (!blob) return

        const file = new File([blob], `posture-${view}-${Date.now()}.png`, {
          type: "image/png",
        })

        onCapture(file, URL.createObjectURL(blob))

        // Close after handing the file over. The camera modal pushed a
        // history entry when it opened, so step back through it rather than
        // calling onClose directly -- otherwise the entry is left behind and
        // the next Android back press closes the site instead of doing
        // nothing.
        window.history.back()
      },
      "image/png",
    )
  }, [view, onCapture, onClose])

  const rollOk = level !== null && level.roll <= LEVEL_LIMIT_DEG
  const pitchOk = level !== null && level.pitch <= LEVEL_LIMIT_DEG
  const isLevel = levelStatus === "active" && rollOk && pitchOk

  const guidesOn = layers.lines || layers.grid
  const pill = (ok: boolean) =>
    `rounded-full px-3 py-1.5 text-[12px] font-medium tabular-nums transition ${
      ok ? "bg-[#1C7A54] text-white" : "bg-white/10 text-white/80"
    }`

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
                <li>Phone on a tripod, at about half the patient&apos;s height. The tripod is part of the clinic setup: the photo is taken only when the phone is within 1.5&deg; of level.</li>
                <li>Tripod 1.5 to 3 m from the patient, in the same spot every visit.</li>
                <li>Patient on the floor marker, feet in the standard position.</li>
                <li>Clothing that shows the shoulders, hips, knees and ankles.</li>
                <li>Head and feet inside the guide lines. A cropped head or foot drops every millimetre measurement from the report.</li>
              </ul>
              <p className="text-[12px] leading-snug text-white/50">
                Set distance and height once on the tripod. Changing them between visits makes the measurements incomparable.
              </p>
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

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 p-8">
            <p className="max-w-xs text-center text-[15px] leading-relaxed">{error}</p>
          </div>
        )}
      </div>

      {/* Bottom panel */}
      <div className="space-y-3 bg-black px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3">
        <p className="text-center text-[13px] leading-snug text-white/60">{GUIDANCE[view]}</p>

        {levelStatus === "active" && level ? (
          <div className="flex items-center justify-center gap-2">
            <span className={pill(rollOk)}>Side {`${level.roll.toFixed(1)}\u00b0`}</span>
            <span className={pill(pitchOk)}>Forward {`${level.pitch.toFixed(1)}\u00b0`}</span>
          </div>
        ) : levelStatus === "denied" ? (
          <div className="space-y-2 text-center">
            <p className="text-[13px] leading-snug text-[#F2B8B5]">
              The level check needs motion access. Without it the photo cannot be taken here.
            </p>
            <button
              type="button"
              onClick={() => void enableLevel()}
              className="h-10 rounded-full bg-white/10 px-4 text-[13px] font-medium"
            >
              Allow motion access
            </button>
          </div>
        ) : levelStatus === "unavailable" ? (
          <p className="text-center text-[13px] leading-snug text-[#F2B8B5]">
            This device cannot report its tilt, so the photo cannot be taken here. Use a phone, or upload a photo instead.
          </p>
        ) : (
          <p className="text-center text-[13px] text-white/50">Starting level check...</p>
        )}

        <div className="flex flex-col items-center gap-1.5">
          <button
            type="button"
            onClick={capture}
            disabled={!ready || !isLevel}
            aria-label="Capture"
            className={`flex h-[76px] w-[76px] items-center justify-center rounded-full border-4 transition ${
              isLevel && ready ? "border-[#3FB68B]" : "border-white/25"
            }`}
          >
            <span
              className={`h-[60px] w-[60px] rounded-full transition ${
                isLevel && ready ? "bg-white" : "bg-white/20"
              }`}
            />
          </button>
          <span className={`text-[13px] font-medium ${isLevel ? "text-[#3FB68B]" : "text-white/60"}`}>
            {isLevel
              ? "Level. Tap to capture"
              : levelStatus === "active"
                ? `Hold the phone straight, both within ${LEVEL_LIMIT_DEG}\u00b0`
                : "Capture is off until the level is checked"}
          </span>
        </div>
      </div>
    </div>
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
