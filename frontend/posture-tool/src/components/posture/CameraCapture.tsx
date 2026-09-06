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
        onClose()
      },
      "image/jpeg",
      0.95,
    )
  }, [view, onCapture, onClose])

  const level = tilt !== null && Math.abs(tilt) <= LEVEL_TOLERANCE_DEG

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
          className="h-full w-full object-cover"
        />

        {ready && <SilhouetteGuide view={view} />}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center p-8">
            <p className="text-center text-sm text-white">{error}</p>
          </div>
        )}
      </div>

      <div className="space-y-3 px-4 py-4">
        <p className="text-xs leading-relaxed text-white/70">
          {GUIDANCE[view]}
        </p>

        {tilt === null ? (
          <button
            type="button"
            onClick={enableTilt}
            className="w-full rounded-lg border border-white/30 py-2 text-xs text-white/80"
          >
            Enable level check
          </button>
        ) : (
          <p
            className={`text-xs ${level ? "text-emerald-400" : "text-amber-400"}`}
          >
            {level
              ? `Camera is level (${tilt}\u00b0)`
              : `Camera is tilted ${tilt}\u00b0. Hold it upright and level with the patient.`}
          </p>
        )}

        <button
          type="button"
          onClick={capture}
          disabled={!ready}
          className="w-full rounded-xl bg-white py-3 font-medium text-slate-900 disabled:opacity-40"
        >
          Capture
        </button>
      </div>
    </div>
  )
}

function SilhouetteGuide({ view }: { view: CaptureView }) {
  return (
    <svg
      viewBox="0 0 100 200"
      preserveAspectRatio="xMidYMid meet"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <g
        fill="none"
        stroke="rgba(255,255,255,0.85)"
        strokeWidth="0.8"
        strokeDasharray="3 2"
      >
        {view === "side" ? (
          <>
            <circle cx="50" cy="22" r="10" />
            <path d="M50 32 L50 96" />
            <path d="M50 44 L46 70" />
            <path d="M50 96 L48 140 L50 178" />
            <path d="M50 178 L60 180" />
          </>
        ) : (
          <>
            <circle cx="50" cy="22" r="10" />
            <path d="M34 44 L66 44" />
            <path d="M50 32 L50 96" />
            <path d="M34 44 L30 78" />
            <path d="M66 44 L70 78" />
            <path d="M38 96 L62 96" />
            <path d="M42 96 L40 178" />
            <path d="M58 96 L60 178" />
          </>
        )}
      </g>

      <g stroke="rgba(255,255,255,0.35)" strokeWidth="0.4">
        <path d="M50 8 L50 192" />
        <path d="M20 178 L80 178" />
      </g>
    </svg>
  )
}
