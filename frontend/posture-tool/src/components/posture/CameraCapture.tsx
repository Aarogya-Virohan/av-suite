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
  const [showSetup, setShowSetup] = useState(true)

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
    type MotionPermission = {
      requestPermission?: () => Promise<"granted" | "denied">
    }

    if (typeof window === "undefined" || !("DeviceMotionEvent" in window)) {
      setLevelStatus("unavailable")
      return
    }

    const api = DeviceMotionEvent as unknown as MotionPermission

    try {
      if (typeof api.requestPermission === "function") {
        const res = await api.requestPermission()
        if (res !== "granted") {
          setLevelStatus("denied")
          return
        }
      }
    } catch {
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

  // The old listener was never removed; this one is, when the camera closes.
  useEffect(() => {
    return () => {
      if (motionHandlerRef.current) {
        window.removeEventListener("devicemotion", motionHandlerRef.current)
        motionHandlerRef.current = null
      }
    }
  }, [])

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

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black">
      <div className="flex items-center justify-between px-4 py-3 text-white">
        <span className="text-sm font-medium">{label}</span>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-3 py-1 text-sm text-white/80"
        >
          Cancel
        </button>
      </div>

      <div className="relative flex-1 overflow-hidden">
        <video
          ref={videoRef}
          playsInline
          muted
          className="h-full w-full object-contain"
        />

        {ready && <SilhouetteGuide layers={layers} />}

        {showSetup && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/95 px-6">
            <div className="w-full max-w-sm space-y-4">
              <h3 className="text-sm font-medium text-white">Before you capture</h3>

              <ul className="space-y-2.5 text-[13px] leading-snug text-white/75">
                <li>Camera on a tripod, roughly at half the patient&apos;s height.</li>
                <li>Tripod 1.5 to 3 m from the patient, in the same spot every visit.</li>
                <li>Patient stands on the floor marker, feet in the standard position.</li>
                <li>Minimal clothing so the shoulders, hips, knees and ankles are visible.</li>
                <li>Whole body inside the frame: the top of the head and the feet both within the guide lines. The calibration is measured from the nose to the ankles, so a cropped head or foot drops every millimetre measurement from the report.</li>
              </ul>

              <p className="text-[11px] leading-snug text-white/45">
                Distance and camera height are set once on the tripod, not adjusted per patient. Changing them between visits makes measurements incomparable.
              </p>

              <button
                type="button"
                onClick={() => setShowSetup(false)}
                className="w-full rounded-xl bg-white py-2.5 text-sm font-medium text-slate-900"
              >
                Got it
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center p-8">
            <p className="text-center text-sm text-white">{error}</p>
          </div>
        )}
      </div>

      <div className="space-y-2 px-3 pb-3 pt-2">
        <div className="flex gap-1.5">
          {(
            [
              ["lines", "Lines"],
              ["grid", "Grid"],
            ] as [keyof GuideLayers, string][]
          ).map(([key, text]) => (
            <button
              key={key}
              type="button"
              onClick={() => setLayers((l) => ({ ...l, [key]: !l[key] }))}
              className={`rounded-full border px-2.5 py-0.5 text-[11px] transition ${
                layers[key]
                  ? "border-white/80 bg-white/90 text-slate-900"
                  : "border-white/25 text-white/50"
              }`}
            >
              {text}
            </button>
          ))}

          <button
            type="button"
            onClick={() => setShowSetup(true)}
            className="rounded-full border border-white/25 px-2.5 py-0.5 text-[11px] text-white/50"
          >
            Setup
          </button>
        </div>

        <p className="text-[11px] leading-snug text-white/60">
          {GUIDANCE[view]}
        </p>

        {levelStatus === "off" || levelStatus === "waiting" ? (
          <button
            type="button"
            onClick={enableLevel}
            disabled={levelStatus === "waiting"}
            className="w-full rounded-lg border border-white/25 py-1.5 text-[11px] text-white/70 disabled:opacity-50"
          >
            {levelStatus === "waiting" ? "Starting level check..." : "Enable level check to capture"}
          </button>
        ) : levelStatus === "active" && level ? (
          <div className="flex items-center justify-between gap-2 text-[11px]">
            <span className={rollOk ? "text-emerald-400" : "text-amber-400"}>
              Side tilt {`${level.roll.toFixed(1)}\u00b0`} {rollOk ? "\u2713" : ""}
            </span>
            <span className={pitchOk ? "text-emerald-400" : "text-amber-400"}>
              Forward tilt {`${level.pitch.toFixed(1)}\u00b0`} {pitchOk ? "\u2713" : ""}
            </span>
            <span className={isLevel ? "text-emerald-400" : "text-white/60"}>
              {isLevel ? "Level" : `Both within ${LEVEL_LIMIT_DEG}\u00b0`}
            </span>
          </div>
        ) : (
          <p className="text-[11px] leading-snug text-rose-300">
            {levelStatus === "denied"
              ? "Motion access was refused, so the level cannot be checked and the photo cannot be captured here. Allow motion access, or upload a photo instead."
              : "This device cannot report its tilt, so the photo cannot be captured here. Use a phone, or upload a photo instead."}
          </p>
        )}

        <button
          type="button"
          onClick={capture}
          disabled={!ready || !isLevel}
          className="w-full rounded-xl bg-white py-2.5 text-sm font-medium text-slate-900 disabled:opacity-30"
        >
          {isLevel || levelStatus !== "active" ? "Capture" : "Hold the phone level to capture"}
        </button>
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
