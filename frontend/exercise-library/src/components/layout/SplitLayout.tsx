"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";

interface SplitLayoutProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  rightCount: number;
}

/**
 * Two panes side by side from lg up. Below that the panes become tabs, so
 * a phone shows one pane at full width instead of two squeezed ones.
 */
export function SplitLayout({ leftPanel, rightPanel, rightCount }: SplitLayoutProps) {
  const [tab, setTab] = useState<"library" | "rx">("library");

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
      <div
        role="tablist"
        aria-label="Sections"
        className="sticky top-16 z-20 flex gap-1 border-b border-line bg-canvas/95 p-2 backdrop-blur lg:hidden"
      >
        {(
          [
            ["library", "Library"],
            ["rx", `Prescription${rightCount ? ` (${rightCount})` : ""}`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              "h-10 flex-1 cursor-pointer rounded-lg text-sm font-semibold transition-colors",
              tab === key ? "bg-card text-ink shadow-card" : "text-muted-foreground hover:text-ink"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <section
        className={cn(
          "min-h-0 flex-col p-4 sm:p-6 lg:flex lg:w-[52%] lg:border-r lg:border-line",
          tab === "library" ? "flex flex-1" : "hidden"
        )}
      >
        {leftPanel}
      </section>
      <section
        className={cn(
          "min-h-0 flex-col bg-card/60 p-4 sm:p-6 lg:flex lg:w-[48%]",
          tab === "rx" ? "flex flex-1" : "hidden"
        )}
      >
        {rightPanel}
      </section>
    </div>
  );
}
