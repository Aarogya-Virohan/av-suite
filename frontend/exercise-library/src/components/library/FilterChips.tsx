import React from "react";
import { Badge } from "@/components/ui/badge";

interface FilterChipsProps {
  parts: string[];
  selectedPart: string | null;
  onSelect: (part: string | null) => void;
}

export function FilterChips({ parts, selectedPart, onSelect }: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      <Badge
        variant={selectedPart === null ? "default" : "secondary"}
        className="cursor-pointer hover:bg-primary/80 transition-colors"
        onClick={() => onSelect(null)}
      >
        All
      </Badge>
      {parts.map((part) => (
        <Badge
          key={part}
          variant={selectedPart === part ? "default" : "secondary"}
          className="cursor-pointer hover:bg-primary/80 transition-colors"
          onClick={() => onSelect(selectedPart === part ? null : part)}
        >
          {part}
        </Badge>
      ))}
    </div>
  );
}
