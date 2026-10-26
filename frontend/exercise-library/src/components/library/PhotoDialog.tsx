"use client";

import React, { useEffect, useRef, useState } from "react";
import { Camera, ImageOff, Loader2, Trash2, X } from "lucide-react";
import { ApiError, deleteExercisePhoto, uploadExercisePhoto } from "@/lib/api";
import { forgetPhoto, useExercisePhoto } from "@/lib/exercisePhotos";
import { toast } from "@/components/ui/toaster";
import type { Exercise, ExercisePhoto, PhotoAngle } from "@/types/exercise";

const ANGLES: { angle: PhotoAngle; label: string }[] = [
  { angle: "front", label: "Front" },
  { angle: "side", label: "Side" },
];

interface PhotoDialogProps {
  exercise: Exercise;
  onClose: () => void;
  onPhotosChange: (exerciseId: string, photos: ExercisePhoto[]) => void;
}

/**
 * The clinic's own photos of an exercise, front and side (founders' answer
 * 2A, 27 Oct 2026). Only this clinic sees them. Photos of patients are not
 * allowed here.
 */
export function PhotoDialog({ exercise, onClose, onPhotosChange }: PhotoDialogProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const photos = exercise.photos ?? [];

  // Latest onClose without re-running the effect on every parent render,
  // which would pull focus back to the close button after each upload.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const setPhoto = (angle: PhotoAngle, photo: ExercisePhoto | null) => {
    const others = photos.filter((p) => p.angle !== angle);
    const next = photo ? [...others, photo] : others;
    next.sort((a, b) => (a.angle === b.angle ? 0 : a.angle === "front" ? -1 : 1));
    onPhotosChange(exercise.id, next);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="photo-dialog-title"
        className="w-full max-w-lg rounded-t-2xl border border-line bg-card p-4 shadow-card sm:rounded-2xl sm:p-5"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id="photo-dialog-title" className="font-display text-base font-bold capitalize text-ink">
              {exercise.name.toLowerCase()}
            </h2>
            <p className="mt-0.5 text-xs text-ink-2">Your clinic&apos;s photos. Only your clinic sees them.</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-9 w-9 shrink-0 cursor-pointer place-items-center rounded-[10px] text-ink-2 hover:bg-grove-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          {ANGLES.map(({ angle, label }) => (
            <PhotoSlot
              key={angle}
              exerciseId={exercise.id}
              angle={angle}
              label={label}
              photo={photos.find((p) => p.angle === angle)}
              onChange={(photo) => setPhoto(angle, photo)}
            />
          ))}
        </div>

        <p className="mt-3 text-xs text-ink-2">
          Use photos of the exercise only. Do not upload photos of patients.
        </p>
      </div>
    </div>
  );
}

interface PhotoSlotProps {
  exerciseId: string;
  angle: PhotoAngle;
  label: string;
  photo: ExercisePhoto | undefined;
  onChange: (photo: ExercisePhoto | null) => void;
}

function PhotoSlot({ exerciseId, angle, label, photo, onChange }: PhotoSlotProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"upload" | "remove" | null>(null);
  const url = useExercisePhoto(exerciseId, photo);

  const upload = async (file: File) => {
    setBusy("upload");
    try {
      const saved = await uploadExercisePhoto(exerciseId, angle, file);
      onChange(saved);
      toast(`${label} photo saved.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save the photo. Please try again.");
    } finally {
      setBusy(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const remove = async () => {
    setBusy("remove");
    try {
      await deleteExercisePhoto(exerciseId, angle);
      forgetPhoto(exerciseId, angle);
      onChange(null);
      toast(`${label} photo removed.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not remove the photo. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-w-0">
      <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="grid aspect-[4/3] w-full place-items-center overflow-hidden rounded-xl border border-line-soft bg-white">
        {busy === "upload" ? (
          <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Uploading" />
        ) : photo && url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={`${label} photo`} className="h-full w-full object-contain" />
        ) : photo && url === "" ? (
          <Loader2 className="h-5 w-5 animate-spin text-[#b9b3a4]" aria-label="Loading" />
        ) : photo ? (
          <span className="px-2 text-center text-xs text-ink-2">Photo could not be loaded</span>
        ) : (
          <ImageOff className="h-5 w-5 text-[#b9b3a4]" aria-hidden />
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void upload(file);
        }}
      />
      <div className="mt-2 flex gap-1.5">
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => inputRef.current?.click()}
          className="flex h-9 flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-[10px] bg-grove px-2 text-[13px] font-semibold text-white shadow-primary hover:bg-grove-hover disabled:cursor-default disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
        >
          <Camera className="h-4 w-4" aria-hidden />
          {photo ? "Replace" : "Add photo"}
        </button>
        {photo && (
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void remove()}
            aria-label={`Remove ${label.toLowerCase()} photo`}
            className="grid h-9 w-9 shrink-0 cursor-pointer place-items-center rounded-[10px] border border-line text-danger hover:bg-danger-wash disabled:cursor-default disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-grove/25"
          >
            {busy === "remove" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  );
}
