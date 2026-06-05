import React from "react";

interface SplitLayoutProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
}

export function SplitLayout({ leftPanel, rightPanel }: SplitLayoutProps) {
  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-muted/30">
      {/* Left Panel */}
      <div className="w-1/2 min-w-[300px] border-r bg-background p-6 overflow-hidden flex flex-col">
        {leftPanel}
      </div>

      {/* Right Panel */}
      <div className="w-1/2 min-w-[300px] bg-background p-6 overflow-hidden flex flex-col">
        {rightPanel}
      </div>
    </div>
  );
}
