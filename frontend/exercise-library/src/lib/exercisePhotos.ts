"use client";

import { useEffect, useState } from "react";
import { fetchExercisePhoto } from "@/lib/api";
import type { ExercisePhoto, PhotoAngle } from "@/types/exercise";

// One blob URL per photo version, shared by every card and dialog that shows
// it. A new upload has a new updatedAt, so it gets a new entry; the old URL
// is released when the photo of that angle changes or is removed.
const cache = new Map<string, Promise<string>>();
const current = new Map<string, string>();

function slot(exerciseId: string, angle: PhotoAngle) {
  return `${exerciseId}:${angle}`;
}

export function forgetPhoto(exerciseId: string, angle: PhotoAngle) {
  const s = slot(exerciseId, angle);
  const key = current.get(s);
  if (!key) return;
  current.delete(s);
  const pending = cache.get(key);
  cache.delete(key);
  pending?.then((url) => URL.revokeObjectURL(url)).catch(() => undefined);
}

function load(exerciseId: string, photo: ExercisePhoto): Promise<string> {
  const s = slot(exerciseId, photo.angle);
  const key = `${s}:${photo.updatedAt}`;
  if (current.get(s) !== key) forgetPhoto(exerciseId, photo.angle);
  let pending = cache.get(key);
  if (!pending) {
    pending = fetchExercisePhoto(exerciseId, photo.angle);
    pending.catch(() => {
      // Let a later render try again.
      if (cache.get(key) === pending) cache.delete(key);
      if (current.get(s) === key) current.delete(s);
    });
    cache.set(key, pending);
    current.set(s, key);
  }
  return pending;
}

/** Blob URL of the clinic photo, "" while loading, null if it failed. */
export function useExercisePhoto(exerciseId: string, photo: ExercisePhoto | undefined): string | null {
  const [state, setState] = useState<{ key: string; url: string | null }>({ key: "", url: "" });
  const key = photo ? `${exerciseId}:${photo.angle}:${photo.updatedAt}` : "";

  useEffect(() => {
    if (!photo) return;
    let alive = true;
    load(exerciseId, photo)
      .then((url) => alive && setState({ key, url }))
      .catch(() => alive && setState({ key, url: null }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (!photo) return null;
  return state.key === key ? state.url : "";
}
