"use client";

import React, { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, X } from "lucide-react";

/*
 * Small toast store, replacing the old window.alert() calls. No library:
 * one listener, at most three toasts, auto-dismiss after 4 s (errors 7 s).
 */

type Tone = "success" | "error";
interface Toast {
  id: number;
  tone: Tone;
  message: string;
}

let nextId = 1;
let toasts: Toast[] = [];
const listeners = new Set<(t: Toast[]) => void>();

function emit() {
  for (const l of listeners) l(toasts);
}

export function toast(message: string, tone: Tone = "success") {
  const id = nextId++;
  toasts = [...toasts, { id, tone, message }].slice(-3);
  emit();
  setTimeout(() => dismiss(id), tone === "error" ? 7000 : 4000);
}

toast.error = (message: string) => toast(message, "error");

function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    listeners.add(setItems);
    return () => {
      listeners.delete(setItems);
    };
  }, []);

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-[72px] z-50 flex flex-col items-center gap-2 px-4 sm:left-auto sm:right-4 sm:items-end"
    >
      {items.map((t) => (
        <div
          key={t.id}
          role={t.tone === "error" ? "alert" : "status"}
          className={`pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm shadow-card animate-in fade-in slide-in-from-top-2 ${
            t.tone === "error"
              ? "border-danger/25 bg-danger-wash text-danger"
              : "border-grove/20 bg-card text-ink"
          }`}
        >
          {t.tone === "error" ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-grove" />
          )}
          <p className="flex-1 leading-snug font-medium">{t.message}</p>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            className="rounded p-0.5 opacity-60 hover:opacity-100"
            aria-label="Dismiss"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
