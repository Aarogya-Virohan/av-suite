"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ExternalLink, LogOut } from "lucide-react";
import { clearSession, fetchMe, type Me } from "@/lib/api";

function initials(me: Me | null): string {
  const f = me?.user.first_name?.trim()?.[0] ?? "";
  const l = me?.user.last_name?.trim()?.[0] ?? "";
  return (f + l || me?.user.email?.[0] || "").toUpperCase();
}

export function Header() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let active = true;
    fetchMe()
      .then((data) => active && setMe(data))
      .catch(() => {
        // Name and clinic are cosmetic here; the page shows its own errors.
      });
    return () => {
      active = false;
    };
  }, []);

  const handleLogout = () => {
    clearSession();
    router.push("/login");
  };

  const fullName = me
    ? `${me.user.first_name ?? ""} ${me.user.last_name ?? ""}`.trim() || me.user.email
    : "";

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-4 border-b border-line bg-card/95 px-4 backdrop-blur sm:px-6">
      <Link href="/" className="flex min-w-0 items-center gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-[10px] bg-white p-1 shadow-[0_0_0_1.5px_rgba(78,136,143,0.35)]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/av-logo-mark.png" alt="" className="h-full w-full object-contain" />
        </span>
        <span className="min-w-0 leading-tight">
          <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-logo-teal-ink">
            AV Suite
          </span>
          <span className="block truncate font-display text-[15px] font-bold text-ink">Exercise Library</span>
        </span>
      </Link>

      <div className="flex items-center gap-2 sm:gap-4">
        <a
          href="https://av-suite.vercel.app"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-ink-2 transition-colors hover:bg-muted hover:text-ink md:flex"
        >
          Posture Tool
          <ExternalLink className="h-3.5 w-3.5" />
        </a>

        {me && (
          <div className="flex items-center gap-2.5 border-l border-line pl-3 sm:pl-4">
            <span
              aria-hidden
              className="grid h-8 w-8 place-items-center rounded-full bg-grove-wash text-xs font-bold text-grove"
            >
              {initials(me)}
            </span>
            <span className="hidden min-w-0 leading-tight sm:block">
              <span className="block max-w-[180px] truncate text-sm font-semibold text-ink">{fullName}</span>
              {me.clinic && (
                <span className="block max-w-[180px] truncate text-xs text-muted-foreground">{me.clinic.name}</span>
              )}
            </span>
          </div>
        )}

        <button
          type="button"
          onClick={handleLogout}
          className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-danger/30 hover:bg-danger-wash hover:text-danger"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Log out</span>
        </button>
      </div>
    </header>
  );
}
