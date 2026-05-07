"use client"

import type { ChangeEvent } from "react"

interface UploadZoneProps {
  setImage: (image: string) => void
}

export default function UploadZone({ setImage }: UploadZoneProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImage(URL.createObjectURL(file))
    }
  }

  return (
    <div className="border-2 border-dashed p-10 text-center">
      <input type="file" onChange={handleChange} />
      <p>Upload Image</p>
    </div>
  )
}
