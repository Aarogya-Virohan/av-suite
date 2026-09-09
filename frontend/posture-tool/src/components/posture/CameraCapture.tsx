"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type CaptureView = "front" | "side" | "back"

interface CameraCaptureProps {
  view: CaptureView
  label: string
  onCapture: (file: File, previewUrl: string) => void
  onClose: () => void
}

// Tilt beyond this is called out. The capture protocol asks for a
// levelled camera; this cannot measure camera height, only tilt, so it
// is a partial check and is worded as guidance rather than a gate.
const LEVEL_TOLERANCE_DEG = 3
// Beyond this the tilt is bad enough to distort landmark positions more
// than the measurements we report. It warns rather than blocks: a small
// share of captures happen without a tripod, and refusing to take the
// photo at all leaves the clinician with nothing, which is worse than a
// flagged imperfect one. The angle is recorded with the capture so a
// questionable frame can be identified later.
const LEVEL_BLOCK_DEG = 10

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
  const [tilt, setTilt] = useState<number | null>(null)
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

  // ---- tilt ----
  // iOS requires an explicit user gesture before orientation events are
  // delivered, so this is requested from a button rather than on mount.
  const enableTilt = useCallback(async () => {
    type OrientationPermission = {
      requestPermission?: () => Promise<"granted" | "denied">
    }

    const api = DeviceOrientationEvent as unknown as OrientationPermission

    try {
      if (typeof api.requestPermission === "function") {
        const res = await api.requestPermission()
        if (res !== "granted") return
      }

      window.addEventListener("deviceorientation", (e) => {
        if (e.beta === null) return
        // beta is front-back tilt; 90 means the phone is upright.
        setTilt(Math.round(e.beta - 90))
      })
    } catch {
      // Tilt is optional guidance; failing to get it must not block capture.
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

    // Quality is deliberately high. Heavy JPEG compression degrades
    // landmark accuracy enough to move a borderline measurement across
    // a severity threshold, which is the whole reason for capturing
    // in-app rather than accepting a forwarded photo.
    canvas.toBlob(
      (blob) => {
        if (!blob) return

        const file = new File([blob], `posture-${view}-${Date.now()}.jpg`, {
          type: "image/jpeg",
        })

        onCapture(file, URL.createObjectURL(blob))

        // Close after handing the file over. The camera modal pushed a
        // history entry when it opened, so step back through it rather than
        // calling onClose directly -- otherwise the entry is left behind and
        // the next Android back press closes the site instead of doing
        // nothing.
        window.history.back()
      },
      "image/jpeg",
      0.95,
    )
  }, [view, onCapture, onClose])

  const absTilt = tilt === null ? null : Math.abs(tilt)
  const level = absTilt !== null && absTilt <= LEVEL_TOLERANCE_DEG
  const severeTilt = absTilt !== null && absTilt > LEVEL_BLOCK_DEG

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

        {tilt === null ? (
          <button
            type="button"
            onClick={enableTilt}
            className="w-full rounded-lg border border-white/25 py-1.5 text-[11px] text-white/70"
          >
            Enable level check
          </button>
        ) : (
          <p
            className={`text-[11px] ${
              severeTilt
                ? "text-rose-400"
                : level
                  ? "text-emerald-400"
                  : "text-amber-400"
            }`}
          >
            {severeTilt
              ? `Camera is tilted ${tilt}\u00b0. Straighten it before capturing -- this much tilt distorts the measurements.`
              : level
                ? `Camera is level (${tilt}\u00b0)`
                : `Camera is tilted ${tilt}\u00b0. Straighten it for a cleaner frame.`}
          </p>
        )}

        <button
          type="button"
          onClick={capture}
          disabled={!ready}
          className="w-full rounded-xl bg-white py-2.5 text-sm font-medium text-slate-900 disabled:opacity-30"
        >
          Capture
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
