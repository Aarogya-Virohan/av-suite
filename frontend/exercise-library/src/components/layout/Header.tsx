import React from "react";
import { Activity } from "lucide-react";

export function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-6">
      <div className="flex items-center gap-2 font-bold text-lg">
        <Activity className="h-6 w-6 text-primary" />
        <span>AarogyaVirohan</span>
      </div>
      <div className="ml-auto flex items-center gap-4 text-sm text-muted-foreground">
        Exercise Library
      </div>
    </header>
  );
}
