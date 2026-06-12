"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Loader2, Lock, Mail, AlertCircle, Building2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const json = await response.json();

      if (!response.ok) {
        throw new Error(
          json?.meta?.error?.message || json?.detail || "Invalid login credentials."
        );
      }

      const token = json?.data?.access_token;
      if (!token) {
        throw new Error("Invalid token payload returned from server.");
      }

      localStorage.setItem("token", token);
      // Store email just for UI reference in the header
      localStorage.setItem("userEmail", email);
      
      router.push("/");
    } catch (err: any) {
      console.error("Login error:", err);
      setError(err.message || "Failed to connect to backend server.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (quickEmail: string) => {
    setEmail(quickEmail);
    setPassword("password123");
    setError(null);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12 relative overflow-hidden font-sans">
      {/* Background Decorative Gradients */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[400px] h-[400px] bg-amber-500/10 rounded-full blur-[150px] pointer-events-none" />

      <div className="w-full max-w-md space-y-8 z-10">
        <div className="flex flex-col items-center text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-amber-500/10 border border-primary/40 shadow-xl shadow-primary/10 mb-4 animate-pulse">
            <Activity className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white">
            AarogyaVirohan
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Clinical Exercise Prescription & Diagnostics
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-8 shadow-2xl shadow-black/40">
          <form onSubmit={handleLogin} className="space-y-6">
            {error && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 p-3.5 text-xs font-semibold text-destructive animate-in fade-in slide-in-from-top-1 duration-200">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-5">
              {/* Email Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Clinic Admin Email
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-slate-500">
                    <Mail className="h-4.5 w-4.5" />
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@clinic.com"
                    className="w-full pl-10.5 pr-4 py-3 bg-slate-950/80 border border-slate-800 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl text-sm text-white placeholder-slate-500 outline-none transition-all"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Password
                  </label>
                </div>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-slate-500">
                    <Lock className="h-4.5 w-4.5" />
                  </span>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10.5 pr-4 py-3 bg-slate-950/80 border border-slate-800 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl text-sm text-white placeholder-slate-500 outline-none transition-all"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-primary hover:bg-primary/90 disabled:bg-primary/50 text-white rounded-xl text-sm font-bold shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Authenticating...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* Quick Seeding Admins Section */}
          <div className="mt-8 pt-6 border-t border-slate-800/80">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-3">
              Quick Test Accounts (Seed Matrix)
            </span>
            <div className="grid grid-cols-1 gap-2.5">
              <button
                type="button"
                onClick={() => handleQuickFill("admin1@avsuite.com")}
                className="flex items-center justify-between text-left p-2.5 rounded-xl border border-slate-800 hover:border-primary/50 hover:bg-primary/5 bg-slate-950/40 text-xs text-slate-300 hover:text-white transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span className="font-semibold">AV Central Clinic</span>
                </div>
                <span className="text-[10px] text-slate-500">admin1@avsuite.com</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill("admin2@avsuite.com")}
                className="flex items-center justify-between text-left p-2.5 rounded-xl border border-slate-800 hover:border-primary/50 hover:bg-primary/5 bg-slate-950/40 text-xs text-slate-300 hover:text-white transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span className="font-semibold">Care & Recovery</span>
                </div>
                <span className="text-[10px] text-slate-500">admin2@avsuite.com</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill("admin3@avsuite.com")}
                className="flex items-center justify-between text-left p-2.5 rounded-xl border border-slate-800 hover:border-primary/50 hover:bg-primary/5 bg-slate-950/40 text-xs text-slate-300 hover:text-white transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span className="font-semibold">Apex Physio Therapy</span>
                </div>
                <span className="text-[10px] text-slate-500">admin3@avsuite.com</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
