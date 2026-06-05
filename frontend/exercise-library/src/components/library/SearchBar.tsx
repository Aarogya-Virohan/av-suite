import React from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  value: string;
  onChange: (val: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative mb-4">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder="Search by name or condition..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9 bg-muted/50 border-transparent focus-visible:border-primary transition-colors focus-visible:ring-primary/20"
      />
    </div>
  );
}
