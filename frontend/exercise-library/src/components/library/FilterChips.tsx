import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Filter, RotateCcw } from "lucide-react";

interface FilterChipsProps {
  parts: string[];
  selectedParts: string[];
  onToggle: (part: string) => void;
  onApply: () => void;
  onClear: () => void;
  isDirty: boolean;
}

export function FilterChips({
  parts,
  selectedParts,
  onToggle,
  onApply,
  onClear,
  isDirty,
}: FilterChipsProps) {
  return (
    <div className="flex flex-col gap-3 mb-6">
      <div className="flex flex-wrap gap-2">
        <Badge
          variant={selectedParts.length === 0 ? "default" : "secondary"}
          className="cursor-pointer hover:bg-primary/80 transition-colors select-none"
          onClick={onClear}
        >
          All
        </Badge>
        {parts.map((part) => {
          const isSelected = selectedParts.includes(part);
          return (
            <Badge
              key={part}
              variant={isSelected ? "default" : "secondary"}
              className="cursor-pointer hover:bg-primary/80 transition-colors select-none"
              onClick={() => onToggle(part)}
            >
              {part}
            </Badge>
          );
        })}
      </div>
      
      <div className="flex items-center gap-2 mt-1">
        <Button
          size="sm"
          onClick={onApply}
          className={`h-8 text-xs font-semibold shadow-sm transition-all duration-200 ${
            isDirty
              ? "bg-primary text-primary-foreground hover:bg-primary/95 animate-pulse"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
          disabled={!isDirty}
        >
          <Filter className="mr-1.5 h-3.5 w-3.5" />
          Apply Filters
        </Button>
        {selectedParts.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            className="h-8 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/50"
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Reset
          </Button>
        )}
      </div>
    </div>
  );
}
