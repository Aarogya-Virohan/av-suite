"use client"

import type { ChangeEvent } from "react"

interface UploadZoneProps {
label: string
setImage: (image: string) => void
setImageFile: (file: File) => void
}

export default function UploadZone({
label,
setImage,
setImageFile,
}: UploadZoneProps) {

const handleChange = (
e: ChangeEvent<HTMLInputElement>,
) => {


const file = e.target.files?.[0]

if (!file) return

setImage(
  URL.createObjectURL(file)
)

setImageFile(file)

}

return ( <div
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

    <h3 className="font-medium text-slate-900">
      {label}
    </h3>

    <p className="text-sm text-slate-500">
      Upload a posture image
    </p>

  </div>

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

</div>

)
}
