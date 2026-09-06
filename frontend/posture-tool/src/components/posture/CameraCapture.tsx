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
  // Portrait frame. The outline is drawn near-full height so that a
  // patient standing inside it is automatically at the right distance
  // and fully in frame -- landmarks near the edge of the frame are the
  // ones the pose model loses first, and a lost ankle invalidates every
  // millimetre measurement in the report.
  const FRONT = [
    "M50 12",
    "c4 0 7 3 7 7",
    "c0 3 -1 6 -3 8",
    "c5 2 12 4 15 8",
    "c3 4 4 12 5 20",
    "l2 18",
    "l-6 2",
    "l-3 -16",
    "l-2 26",
    "l-2 30",
    "l-1 42",
    "l-7 0",
    "l-2 -42",
    "l-2 -22",
    "l-2 22",
    "l-2 42",
    "l-7 0",
    "l-1 -42",
    "l-2 -30",
    "l-2 -26",
    "l-3 16",
    "l-6 -2",
    "l2 -18",
    "c1 -8 2 -16 5 -20",
    "c3 -4 10 -6 15 -8",
    "c-2 -2 -3 -5 -3 -8",
    "c0 -4 3 -7 7 -7",
    "z",
  ].join(" ")

  const SIDE = [
    "M52 12",
    "c5 0 8 3 8 8",
    "c0 4 -2 7 -5 9",
    "c6 2 10 6 11 12",
    "l2 22",
    "l-5 1",
    "l-2 -14",
    "l-1 24",
    "c0 8 2 14 2 22",
    "l-1 34",
    "l-7 0",
    "l-1 -34",
    "l-2 -20",
    "l-3 20",
    "l-2 34",
    "l-7 0",
    "l2 -36",
    "c0 -10 1 -20 2 -30",
    "l-1 -22",
    "c1 -8 5 -14 12 -17",
    "c-3 -2 -5 -5 -5 -9",
    "c0 -5 3 -8 8 -8",
    "z",
  ].join(" ")

  return (
    <svg
      viewBox="0 0 100 200"
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <path
        d={view === "side" ? SIDE : FRONT}
        fill="rgba(255,255,255,0.10)"
        stroke="rgba(255,255,255,0.75)"
        strokeWidth="0.7"
        strokeLinejoin="round"
      />

      {/* Floor line: the patient's feet belong on it, which fixes both
          distance and the vertical position of the ankles in frame. */}
      <path
        d="M18 190 L82 190"
        stroke="rgba(255,255,255,0.45)"
        strokeWidth="0.6"
        strokeDasharray="4 3"
      />
    </svg>
  )
}
