"use client"

import Image from "next/image"

interface ImagePreviewProps {
  image: string | null
}

export default function ImagePreview({ image }: ImagePreviewProps) {
  if (!image) return null

  return (
    <Image
      src={image}
      alt="Uploaded posture preview"
      width={256}
      height={256}
      unoptimized
      className="w-64 mt-4 h-auto"
    />
  )
}
