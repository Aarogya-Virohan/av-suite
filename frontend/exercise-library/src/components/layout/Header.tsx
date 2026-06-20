"use client";

import React, { useEffect, useState } from "react";
import { Activity, LogOut, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export function Header() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    // Only access localStorage on client side
    const storedEmail = localStorage.getItem("userEmail");
    setEmail(storedEmail);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userEmail");
    router.push("/login");
  };

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background px-6">
      <Link href="/">
        <div className="flex items-center gap-2 font-bold text-lg cursor-pointer hover:opacity-95">
          <Activity className="h-6 w-6 text-primary" />
          <span>AarogyaVirohan</span>
        </div>
      </Link>
      
      <div className="flex items-center gap-6 text-sm font-semibold">
        <Link href="/" className="text-muted-foreground hover:text-primary transition-colors">
          Exercise Library
        </Link>
        {/* Links out to the real, clinically-validated Posture Tool app (separate
            deployment) instead of the internal /posture page, which only embedded an
            unfinished placeholder/demo tool. */}
        <a
          href="https://av-suite.vercel.app"
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground hover:text-primary transition-colors"
        >
          Posture Diagnostics
        </a>

        {email && (
          <div className="flex items-center gap-4 border-l pl-6 border-border">
            <div className="flex items-center gap-2 text-muted-foreground font-normal">
              <User className="h-4 w-4 text-primary" />
              <span className="text-xs max-w-[150px] truncate">{email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-150 hover:bg-destructive/10 text-slate-700 hover:text-destructive border border-slate-200 hover:border-destructive/20 rounded-lg text-xs font-bold transition-all cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

