"use client";

import React, { useEffect, useRef } from "react";
import { Loader2, SearchX } from "lucide-react";
import { Exercise } from "@/types/exercise";
import { ExerciseCard } from "./ExerciseCard";
import { cn } from "@/lib/utils";

interface ExerciseListProps {
  exercises: Exercise[];
  addedIds: string[];
  onAdd: (exercise: Exercise) => void;
  stale: boolean;
  onReset: () => void;
  hasFilters: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  loadMoreError: string | null;
  onLoadMore: () => void;
  onEditPhotos?: (exercise: Exercise) => void;
}

/**
 * The next page loads when the end of the list scrolls into view. A plain
 * "Load more" button is there too (keyboard, and a fallback if the
 * observer does not fire).
 */
export function ExerciseList({
  exercises,
  addedIds,
  onAdd,
  stale,
  onReset,
  hasFilters,
  hasMore,
  loadingMore,
  loadMoreError,
  onLoadMore,
  onEditPhotos,
}: ExerciseListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef(onLoadMore);
  useEffect(() => {
    loadMoreRef.current = onLoadMore;
  }, [onLoadMore]);

  const canAutoLoad = hasMore && !loadingMore && !stale && !loadMoreError;

  useEffect(() => {
    if (!canAutoLoad) return;
    const target = sentinelRef.current;
    if (!target) return;
    // On phones the list is not its own scroll box (the page scrolls), so the
    // viewport is the root there; on desktop it is the list.
    const box = scrollRef.current;
    const root = box && box.scrollHeight > box.clientHeight ? box : null;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) loadMoreRef.current();
      },
      { root, rootMargin: "400px 0px" }
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [canAutoLoad, exercises.length]);

  if (exercises.length === 0 && !stale) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-muted text-muted-foreground">
          <SearchX className="h-5 w-5" />
        </span>
        <p className="font-semibold text-ink">No exercises match</p>
        {hasFilters && (
          <button type="button" onClick={onReset} className="cursor-pointer text-sm font-semibold text-grove hover:text-grove-hover">
            Clear search and filters
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      aria-busy={stale || loadingMore}
      className={cn(
        "-mr-2 min-h-0 flex-1 space-y-2.5 overflow-y-auto pb-6 pr-2 transition-opacity",
        stale && "opacity-60"
      )}
    >
      {exercises.map((exercise) => (
        <ExerciseCard
          key={exercise.id}
          exercise={exercise}
          isAdded={addedIds.includes(exercise.id)}
          onAdd={onAdd}
          onEditPhotos={onEditPhotos}
        />
      ))}

      <div ref={sentinelRef} aria-hidden className="h-px" />
      {hasMore && (
        <div className="flex flex-col items-center gap-1.5 py-2">
          {loadMoreError && <p className="text-xs font-medium text-danger">{loadMoreError}</p>}
          <button
            type="button"
            onClick={onLoadMore}
            disabled={loadingMore}
            className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-line bg-card px-4 text-sm font-semibold text-ink-2 hover:border-grove/40 hover:text-ink disabled:cursor-default disabled:opacity-70"
          >
            {loadingMore && <Loader2 className="h-4 w-4 animate-spin text-grove" />}
            {loadingMore ? "Loading..." : loadMoreError ? "Try again" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
