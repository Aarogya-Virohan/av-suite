import React from "react";
import { Exercise } from "@/types/exercise";
import { ExerciseCard } from "./ExerciseCard";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ExerciseListProps {
  exercises: Exercise[];
  addedIds: string[];
  onAdd: (exercise: Exercise) => void;
}

export function ExerciseList({ exercises, addedIds, onAdd }: ExerciseListProps) {
  if (exercises.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        No exercises found.
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1 pr-4 -mr-4 min-h-0">
      <div className="pb-4">
        {exercises.map((exercise) => (
          <ExerciseCard
            key={exercise.id}
            exercise={exercise}
            isAdded={addedIds.includes(exercise.id)}
            onAdd={onAdd}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
