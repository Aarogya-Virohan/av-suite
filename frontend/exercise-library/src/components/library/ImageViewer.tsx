"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { displayTitle } from "@/lib/displayTitle";

interface ImageViewerProps {
  src: string;
  title: string;
  onClose: () => void;
}

/** Full-size view of an exercise picture. Escape, the X or a click outside closes it. */
export function ImageViewer({ src, title, onClose }: ImageViewerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    closeRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center bg-midnight/70 p-3 sm:p-6"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-full w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-line px-4 py-2.5">
          <p className="min-w-0 flex-1 truncate font-display text-[15px] font-bold text-ink">
            {displayTitle(title)}
          </p>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-ink-2 hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={title}
          referrerPolicy="no-referrer"
          className="max-h-[calc(100vh-7rem)] w-full object-contain"
        />
      </div>
    </div>
  );
}
