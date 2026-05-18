"use client"

import type { ChangeEvent } from "react"

interface UploadZoneProps {
  setImage: (image: string) => void
  setImageFile: (file: File) => void
}

export default function UploadZone({
  setImage,
  setImageFile
}: UploadZoneProps) {

  const handleChange = (
    e: ChangeEvent<HTMLInputElement>
  ) => {

    const file = e.target.files?.[0]

    if (file) {

      const preview =
        URL.createObjectURL(file)

      setImage(preview)

      setImageFile(file)
    }
  }

  return (
    <div className="rounded-2xl border-2 border-dashed border-slate-300 p-10 text-center">

      <input
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="mx-auto block"
      />

      <p className="mt-4 text-slate-600">
        Upload posture image
      </p>

    </div>
  )
}