import React, { useState } from "react";
import { Exercise } from "@/types/exercise";
import { Camera, Check, ImageOff, Lock, Play, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useExercisePhoto } from "@/lib/exercisePhotos";

interface ExerciseCardProps {
  exercise: Exercise;
  isAdded: boolean;
  onAdd: (exercise: Exercise) => void;
  /** Shown only to users who may add clinic photos (exercises.edit). */
  onEditPhotos?: (exercise: Exercise) => void;
}

export function ExerciseCard({ exercise, isAdded, onAdd, onEditPhotos }: ExerciseCardProps) {
  const [imgFailed, setImgFailed] = useState(false);
  // The clinic's own front photo comes first, then the library picture.
  const front = exercise.photos?.find((p) => p.angle === "front") ?? exercise.photos?.[0];
  const clinicUrl = useExercisePhoto(exercise.id, front);
  const showClinic = !!front && clinicUrl !== null;
  const showImage = !showClinic && exercise.imageUrl && !imgFailed;
  const photoCount = exercise.photos?.length ?? 0;

  return (
    <article className="group flex gap-3.5 rounded-2xl border border-line bg-card p-3 shadow-card transition-colors hover:border-grove/30">
      <div className="grid h-[76px] w-[96px] shrink-0 place-items-center overflow-hidden rounded-xl border border-line-soft bg-white">
        {showClinic ? (
          clinicUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={clinicUrl} alt="" className="h-full w-full object-contain" />
          ) : (
            <span className="h-full w-full animate-pulse bg-grove-wash" aria-hidden />
          )
        ) : showImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={exercise.imageUrl}
            alt=""
            loading="lazy"
            decoding="async"
            referrerPolicy="no-referrer"
            onError={() => setImgFailed(true)}
            className="h-full w-full object-contain"
          />
        ) : exercise.videoUrl ? (
          <a
            href={exercise.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Watch the ${exercise.name} demo video (opens in a new tab)`}
            className="flex h-full w-full flex-col items-center justify-center gap-1 text-grove transition-colors hover:bg-grove-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
          >
            <Play className="h-5 w-5" aria-hidden />
            <span className="text-[11px] font-semibold">Watch video</span>
          </a>
        ) : (
          <ImageOff className="h-5 w-5 text-[#b9b3a4]" aria-hidden />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-display text-[15px] font-bold capitalize leading-snug text-ink">
              {exercise.name.toLowerCase()}
            </h3>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="rounded-md bg-grove-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-grove">
                {exercise.bodyPart}
              </span>
              {photoCount > 0 && (
                <span className="rounded-md bg-info-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-info">
                  Clinic photo{photoCount > 1 ? "s" : ""}
                </span>
              )}
              {!exercise.isFree && (
                <span className="inline-flex items-center gap-1 rounded-md bg-warn-wash px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-warn">
                  <Lock className="h-2.5 w-2.5" />
                  Paid
                </span>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
          {onEditPhotos && (
            <button
              type="button"
              onClick={() => onEditPhotos(exercise)}
              aria-label={`Clinic photos for ${exercise.name}`}
              title="Clinic photos"
              className="grid h-9 w-9 cursor-pointer place-items-center rounded-[10px] border border-line text-grove transition-colors hover:bg-grove-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
            >
              <Camera className="h-4 w-4" />
            </button>
          )}
          <button
            type="button"
            disabled={isAdded}
            onClick={() => onAdd(exercise)}
            aria-label={isAdded ? `${exercise.name} added` : `Add ${exercise.name}`}
            className={cn(
              "flex h-9 shrink-0 cursor-pointer items-center gap-1.5 rounded-[10px] px-3 text-[13px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25",
              isAdded
                ? "cursor-default bg-ok-wash text-ok"
                : "bg-grove text-white shadow-primary hover:bg-grove-hover"
            )}
          >
            {isAdded ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {isAdded ? "Added" : "Add"}
          </button>
          </div>
        </div>
        {exercise.instructions && (
          <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-ink-2">{exercise.instructions}</p>
        )}
      </div>
    </article>
  );
}
