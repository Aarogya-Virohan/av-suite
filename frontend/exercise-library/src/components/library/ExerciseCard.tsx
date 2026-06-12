import React from "react";
import { Exercise } from "@/types/exercise";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, Lock } from "lucide-react";

interface ExerciseCardProps {
  exercise: Exercise;
  isAdded: boolean;
  onAdd: (exercise: Exercise) => void;
}

export function ExerciseCard({ exercise, isAdded, onAdd }: ExerciseCardProps) {
  return (
    <Card className="mb-3 overflow-hidden border-border/50 hover:border-primary/30 transition-all hover:shadow-md bg-card/50">
      <CardContent className="p-4 flex flex-col gap-2 relative">
        <div className="flex justify-between items-start gap-4">
          <div className="flex-1">
            <h3 className="font-semibold text-base leading-tight mb-1">{exercise.name}</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
              <span className="font-medium text-primary/80">{exercise.bodyPart}</span>
              <span>•</span>
              <span>{exercise.condition}</span>
              {!exercise.isFree && (
                <>
                  <span>•</span>
                  <span className="inline-flex items-center gap-1 font-semibold text-amber-600 bg-amber-500/10 px-1.5 py-0.5 rounded text-[10px] uppercase">
                    <Lock className="h-2.5 w-2.5" />
                    Paid Library
                  </span>
                </>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {exercise.instructions}
            </p>
          </div>
          <Button
            variant={isAdded ? "secondary" : "default"}
            size="sm"
            className="shrink-0 transition-all"
            disabled={isAdded}
            onClick={() => onAdd(exercise)}
          >
            {isAdded ? (
              <>
                <Check className="mr-1.5 h-3.5 w-3.5" />
                Added
              </>
            ) : (
              "+ Add"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

