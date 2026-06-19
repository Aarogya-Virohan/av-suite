"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Loader2, Save, Users, Award, ShieldAlert, ArrowLeft } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchPatients, savePostureSession } from "@/lib/api";
import Link from "next/link";

export default function PosturePage() {
  const router = useRouter();
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [cachedPayload, setCachedPayload] = useState<any | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Fetch patients on mount with auth guard check
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadPatients() {
      try {
        const data = await fetchPatients();
        setPatients(data);
        if (data.length > 0) {
          setSelectedPatientId(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load patients", err);
      }
    }
    loadPatients();
  }, [router]);

  // Listen for analysis complete postMessage from the iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Check if message is the posture result
      if (event.data && event.data.type === "POSTURE_DIAGNOSTIC_COMPLETE") {
        console.log("Received posture diagnostic payload:", event.data.payload);
        setCachedPayload(event.data.payload);
        
        // Show indicator to save
        alert("Musculoskeletal metrics received! Use the patient panel at the top right to link and persist this session.");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const handleSaveToDatabase = async () => {
    if (!selectedPatientId) {
      alert("Please select a patient before saving.");
      return;
    }
    if (!cachedPayload) {
      alert("Please complete the diagnostics in the tool and click 'SAVE TO PATIENT FILE' first.");
      return;
    }

    setIsSaving(true);
    setSaveStatus("idle");
    try {
      const payload = {
        patient_id: selectedPatientId,
        overall_confidence: cachedPayload.overall_confidence,
        annotated_front_image: undefined,
        annotated_back_image: undefined,
        annotated_side_image: undefined,
        measurements: cachedPayload.measurements,
      };

      await savePostureSession(payload);
      setSaveStatus("success");
      setCachedPayload(null); // Clear cache after success
      alert("Biomechanical posture metrics successfully saved to database!");
    } catch (err) {
      console.error(err);
      setSaveStatus("error");
      alert("Failed to save posture analysis to patient profile.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
      {/* Top Navbar */}
      <div className="top-nav bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <Award className="h-5 w-5 text-primary" />
              Biomechanical Diagnostics
            </h1>
            <p className="text-xs text-slate-400">MediaPipe BlazePose Musculoskeletal Engine</p>
          </div>
        </div>

        {/* Linking Panel */}
        <div className="flex items-center gap-3 bg-slate-800/50 p-2 rounded-xl border border-slate-700/50 w-full md:w-auto">
          <div className="flex flex-col gap-0.5 shrink-0">
            <Label className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">Link to Profile</Label>
            <Select value={selectedPatientId} onValueChange={(val) => setSelectedPatientId(val || "")}>
              <SelectTrigger className="h-8 w-[180px] bg-slate-900 border-slate-700 text-xs shadow-sm text-white">
                <SelectValue placeholder="Select patient...">
                  {selectedPatientId && patients.length > 0 ? (
                    (() => {
                      const selectedPatient = patients.find((p) => p.id === selectedPatientId);
                      return selectedPatient
                        ? `${selectedPatient.first_name} ${selectedPatient.last_name}`
                        : undefined;
                    })()
                  ) : undefined}
                </SelectValue>
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700 text-white">
                {patients.map((pat) => (
                  <SelectItem key={pat.id} value={pat.id} className="text-xs focus:bg-slate-800 focus:text-white">
                    {pat.first_name} {pat.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            size="sm"
            onClick={handleSaveToDatabase}
            disabled={isSaving || !cachedPayload}
            className="h-8 text-xs font-semibold px-3 flex items-center gap-1.5 transition-all shadow-md shadow-primary/20 hover:shadow-primary/30"
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {cachedPayload ? "Save Analysis" : "Run Diagnostics"}
          </Button>
        </div>
      </div>

      {/* Embedded Iframe Container */}
      <div className="flex-1 w-full bg-slate-950 relative min-h-0">
        {cachedPayload && (
          <div className="absolute top-4 left-4 right-4 bg-amber-500/10 border border-amber-500/30 text-amber-500 p-3 rounded-xl flex items-center gap-3 z-30 shadow-lg backdrop-blur-md">
            <ShieldAlert className="h-5 w-5 shrink-0" />
            <div className="text-xs font-medium">
              Diagnostic data cached successfully! Ready to link to patient and click "Save Analysis" above.
            </div>
          </div>
        )}

        <iframe
          ref={iframeRef}
          src="/posture-tool.html"
          className="w-full h-[calc(100vh-80px)] border-0"
          title="Kinetix Biomechanical Tool"
        />
      </div>
    </div>
  );
}
