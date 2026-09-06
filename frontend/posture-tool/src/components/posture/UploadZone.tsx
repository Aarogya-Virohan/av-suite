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
}

export default function UploadZone({
  label,
  view,
  setImage,
  setImageFile,
}: UploadZoneProps) {
  const [cameraOpen, setCameraOpen] = useState(false)

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]

    if (!file) return

    setImage(URL.createObjectURL(file))

    setImageFile(file)
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
            setImage(previewUrl)
            setImageFile(file)
          }}
          onClose={() => setCameraOpen(false)}
        />
      )}
    </div>
  )
}
