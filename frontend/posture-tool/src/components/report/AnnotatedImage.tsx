interface Props {
  src: string
  alt: string
}

export default function AnnotatedImage({
  src,
  alt
}: Props) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200">

      <img
        src={src}
        alt={alt}
        className="h-full w-full object-cover"
      />

    </div>
  )
}