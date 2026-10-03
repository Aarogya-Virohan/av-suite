"use client"

import type { ChangeEvent } from "react"
import { useState } from "react"

import CameraCapture from "./CameraCapture"
import type { CaptureView } from "./CameraCapture"

interface UploadZoneProps {
  label: string
  view: CaptureView
  setImage: (image: string) => void
  setImageFile: (file: File) => void
  setSource: (source: "camera" | "upload") => void
}

export default function UploadZone({
  label,
  view,
  setImage,
  setImageFile,
  setSource,
}: UploadZoneProps) {
  const [cameraOpen, setCameraOpen] = useState(false)
  const [thumb, setThumb] = useState<string | null>(null)
  const [source, setLocalSource] = useState<"camera" | "upload" | null>(null)

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]

    if (!file) return

    const url = URL.createObjectURL(file)

    setThumb(url)
    setImage(url)

    setImageFile(file)

    setLocalSource("upload")
    setSource("upload")
  }

  return (
    <div
      className="
        rounded-2xl
        border-2
        border-dashed
        border-slate-300
        bg-white
        p-6
      "
    >
      <div className="mb-3">
        <h3 className="font-medium text-slate-900">{label}</h3>

        <p className="text-sm text-slate-500">
          Capture with the camera for the most reliable result, or upload an
          existing photo.
        </p>

        <p className="mt-2 text-xs leading-snug text-slate-500">
          An uploaded photo is measured the same way but cannot be checked
          against the capture protocol. For it to be comparable with the
          patient&apos;s other visits it needs the whole body in frame from
          head to feet, the camera level and at about half the
          patient&apos;s height, the same distance each visit, and clothing
          that leaves the shoulders, hips, knees and ankles visible. A
          screenshot or a photo of a screen will not measure correctly.
        </p>
      </div>

      <button
        type="button"
        onClick={() => setCameraOpen(true)}
        className="
          mb-3
          block
          w-full
          rounded-lg
          bg-slate-900
          p-2
          text-sm
          font-medium
          text-white
        "
      >
        Use camera
      </button>

      {thumb && (
        <div className="mb-3 flex items-center gap-3 rounded-lg bg-emerald-50 p-2">
          <img
            src={thumb}
            alt=""
            className="h-14 w-14 rounded object-cover"
          />
          <span className="text-sm font-medium text-emerald-800">
            {source === "upload" ? "Uploaded" : "Captured"}
          </span>
        </div>
      )}

      <input
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="
          block
          w-full
          cursor-pointer
          rounded-lg
          border
          border-slate-200
          p-2
          text-sm
        "
      />

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
