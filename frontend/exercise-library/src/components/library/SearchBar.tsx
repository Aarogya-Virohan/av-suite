import React from "react";
import { Loader2, Search, X } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (val: string) => void;
  busy?: boolean;
}

export function SearchBar({ value, onChange, busy }: SearchBarProps) {
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767b93]" />
      <input
        type="search"
        aria-label="Search exercises"
        placeholder="Search exercises by name"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onChange("")}
        className="h-11 w-full rounded-[10px] border border-line bg-card pl-10 pr-10 text-sm text-ink placeholder:text-[#767b93] transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 [&::-webkit-search-cancel-button]:hidden"
      />
      <span className="absolute right-3 top-1/2 -translate-y-1/2">
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin text-grove" />
        ) : value ? (
          <button
            type="button"
            onClick={() => onChange("")}
            className="grid h-5 w-5 cursor-pointer place-items-center rounded-full text-[#767b93] hover:bg-muted hover:text-ink"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </span>
    </div>
  );
}
