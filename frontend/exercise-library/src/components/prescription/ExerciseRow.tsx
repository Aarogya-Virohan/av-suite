import React from "react";
import { PrescriptionItem } from "@/types/exercise";
import { DosageFields } from "./DosageFields";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

interface ExerciseRowProps {
  item: PrescriptionItem;
  onChange: (updatedItem: PrescriptionItem) => void;
  onRemove: (id: string) => void;
}

export function ExerciseRow({ item, onChange, onRemove }: ExerciseRowProps) {
  return (
    <Card className="mb-3 border-border/60 bg-card/40 shadow-sm relative group overflow-hidden transition-all hover:border-primary/40 hover:shadow-md">
      <div className="absolute top-0 left-0 w-1 h-full bg-primary/80 transition-all group-hover:bg-primary"></div>
      <CardContent className="p-4 pl-5 relative">
        <div className="flex justify-between items-start mb-1">
          <h4 className="font-semibold text-sm leading-tight pr-6">
            {item.exercise.name}
          </h4>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 absolute top-3 right-3 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100"
            onClick={() => onRemove(item.exercise.id)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <DosageFields item={item} onChange={onChange} />
      </CardContent>
    </Card>
  );
}
