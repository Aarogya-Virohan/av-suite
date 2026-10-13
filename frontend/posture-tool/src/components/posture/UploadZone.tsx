"use client"

/*
 * One photograph slot on the intake screen: guided camera capture first,
 * upload as the fallback. Same props as before the 11 October 2026
 * redesign, so the page logic around it is unchanged.
 *
 * An uploaded photo is measured the same way but is not checked against the
 * capture protocol, and the PDF says so. The long explanation of what a
 * usable upload needs now sits behind "What makes a good photo?" instead of
 * filling every card.
 */

import type { ChangeEvent } from "react"
import { useId, useState } from "react"

import CameraCapture, { requestMotionPermission } from "./CameraCapture"
import type { CaptureView } from "./CameraCapture"

interface UploadZoneProps {
  label: string
  view: CaptureView
  setImage: (image: string) => void
  setImageFile: (file: File) => void
  setSource: (source: "camera" | "upload") => void
  required?: boolean
  // "Front photo is required", shown after a Continue with this slot empty.
  error?: string | null
}

function ViewFigure({ view }: { view: CaptureView }) {
  // A plain figure so an empty slot shows which way the patient faces.
  return (
    <svg viewBox="0 0 60 120" className="h-20 w-10 text-[#C9C0AA]" aria-hidden>
      <circle cx="30" cy="14" r="9" fill="currentColor" />
      {view === "side" ? (
        <>
          <rect x="24" y="26" width="13" height="40" rx="6" fill="currentColor" />
          <rect x="25" y="64" width="10" height="46" rx="5" fill="currentColor" />
          <path d="M38 12 l5 3 l-5 2 z" fill="currentColor" />
        </>
      ) : (
        <>
          <rect x="17" y="26" width="26" height="40" rx="8" fill="currentColor" />
          <rect x="18" y="64" width="10" height="46" rx="5" fill="currentColor" />
          <rect x="32" y="64" width="10" height="46" rx="5" fill="currentColor" />
          <rect x="9" y="28" width="7" height="34" rx="3.5" fill="currentColor" />
          <rect x="44" y="28" width="7" height="34" rx="3.5" fill="currentColor" />
          {view === "front" && <circle cx="30" cy="16" r="2" fill="#F3EEE2" />}
        </>
      )}
    </svg>
  )
}

export default function UploadZone({
  label,
  view,
  setImage,
  setImageFile,
  setSource,
  required = false,
  error = null,
}: UploadZoneProps) {
  const [cameraOpen, setCameraOpen] = useState(false)
  const [thumb, setThumb] = useState<string | null>(null)
  const [source, setLocalSource] = useState<"camera" | "upload" | null>(null)
  const inputId = useId()

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const url = URL.createObjectURL(file)
    setThumb(url)
    setImage(url)
    setImageFile(file)
    setLocalSource("upload")
    setSource("upload")
    // Lets the same file be chosen again after a retake.
    e.target.value = ""
  }

  return (
    <div className={`flex flex-row overflow-hidden rounded-2xl border bg-[#FFFDF7] sm:flex-col ${error ? "border-[#B4231B]" : "border-[#E3DCCB]"}`}>
      <div className="relative flex w-28 flex-none items-center justify-center bg-[#F3EEE2] sm:aspect-[3/4] sm:w-auto">
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt={`${label} photograph`} className="absolute inset-0 h-full w-full object-cover" />
        ) : (
          <ViewFigure view={view} />
        )}
        {thumb && source && (
          <span
            className={`absolute left-1.5 top-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium backdrop-blur-md sm:left-2 sm:top-2 sm:px-2.5 sm:py-1 sm:text-[11px] ${
              source === "camera" ? "bg-[#1C7A54]/90 text-white" : "bg-[#FBF3E6]/95 text-[#6B4A12]"
            }`}
          >
            {source === "camera" ? "Captured" : "Uploaded"}
          </span>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
        <p className="text-[15px] font-semibold text-[#141A33]">
          {label}
          {required && (
            <span className="ml-0.5 text-[#B4231B]" aria-hidden="true">
              *
            </span>
          )}
          {source === "upload" && (
            <span className="ml-2 text-[12px] font-normal text-[#A8670F]">not checked</span>
          )}
        </p>
        <button
          type="button"
          onClick={() => {
            // Must start inside this tap for iOS to grant motion access.
            void requestMotionPermission()
            setCameraOpen(true)
          }}
          className="h-10 rounded-xl bg-[#4E888F] text-[13px] font-semibold text-white transition hover:bg-[#3B6A70]"
        >
          {thumb ? "Retake with camera" : "Use camera"}
        </button>
        <label
          htmlFor={inputId}
          className="flex h-10 cursor-pointer items-center justify-center rounded-xl border border-[#E3DCCB] text-[13px] font-medium text-[#141A33] transition hover:bg-[#F3EEE2]"
        >
          {thumb ? "Replace with upload" : "Upload photo"}
        </label>
        <input id={inputId} type="file" accept="image/*" onChange={handleChange} className="sr-only" />
        {error && (
          <p role="alert" className="text-[12px] font-medium text-[#B4231B]">
            {error}
          </p>
        )}
      </div>

      {cameraOpen && (
        <CameraCapture
          view={view}
          label={label}
          onCapture={(file, previewUrl) => {
            setThumb(previewUrl)
            setImage(previewUrl)
            setImageFile(file)
            setLocalSource("camera")
            setSource("camera")
          }}
          onClose={() => setCameraOpen(false)}
        />
      )}
    </div>
  )
}
