import React from "react";
import { SearchX } from "lucide-react";
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
}

export function ExerciseList({ exercises, addedIds, onAdd, stale, onReset, hasFilters }: ExerciseListProps) {
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
      aria-busy={stale}
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
        />
      ))}
    </div>
  );
}
