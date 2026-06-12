"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { SplitLayout } from "@/components/layout/SplitLayout";
import { SearchBar } from "@/components/library/SearchBar";
import { FilterChips } from "@/components/library/FilterChips";
import { ExerciseList } from "@/components/library/ExerciseList";
import { PrescriptionBuilder } from "@/components/prescription/PrescriptionBuilder";
import { A4PrintView } from "@/components/report/A4PrintView";

import { Exercise, PrescriptionItem } from "@/types/exercise";
import { fetchExercises } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  const router = useRouter();
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedParts, setSelectedParts] = useState<string[]>([]);
  const [appliedParts, setAppliedParts] = useState<string[]>([]);
  const [allBodyPartsList, setAllBodyPartsList] = useState<string[]>([]);
  const [showPrintView, setShowPrintView] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Authentication Route Guard & Initial Data Fetch
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadData() {
      setIsLoading(true);
      try {
        const exData = await fetchExercises();
        setExercises(exData);
        // Extract all unique body parts from the complete exercise list
        const parts = new Set(exData.map((e) => e.bodyPart));
        setAllBodyPartsList(Array.from(parts).filter(Boolean));
      } catch (err: any) {
        console.error("Data loading error:", err);
        setAuthError(err.message || "Failed to connect to backend api.");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [router]);

  // Fetch exercises dynamically on search or applied filters change
  useEffect(() => {
    let active = true;
    async function loadFiltered() {
      if (!localStorage.getItem("token")) return;
      try {
        const bodyPartStr = appliedParts.length > 0 ? appliedParts.join(",") : undefined;
        const data = await fetchExercises(searchQuery || undefined, bodyPartStr);
        if (active) {
          setExercises(data);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadFiltered();
    return () => {
      active = false;
    };
  }, [searchQuery, appliedParts]);

  const isDirty = useMemo(() => {
    if (selectedParts.length !== appliedParts.length) return true;
    const sortedSel = [...selectedParts].sort();
    const sortedApp = [...appliedParts].sort();
    return sortedSel.some((val, idx) => val !== sortedApp[idx]);
  }, [selectedParts, appliedParts]);

  // Actions for body part filters
  const togglePartFilter = (part: string) => {
    setSelectedParts((prev) =>
      prev.includes(part) ? prev.filter((p) => p !== part) : [...prev, part]
    );
  };

  const applyPartFilters = () => {
    setAppliedParts(selectedParts);
  };

  const clearPartFilters = () => {
    setSelectedParts([]);
    setAppliedParts([]);
  };

  const addedIds = useMemo(() => prescription.map((p) => p.exercise.id), [prescription]);

  // Actions
  const addExercise = (exercise: Exercise) => {
    setPrescription((prev) => [
      ...prev,
      {
        exercise,
        sets: exercise.sets,
        reps: exercise.reps,
        hold: exercise.hold,
        frequency: exercise.frequency,
      },
    ]);
  };

  const updatePrescriptionItem = (updatedItem: PrescriptionItem) => {
    setPrescription((prev) =>
      prev.map((item) =>
        item.exercise.id === updatedItem.exercise.id ? updatedItem : item
      )
    );
  };

  const removeExercise = (id: string) => {
    setPrescription((prev) => prev.filter((item) => item.exercise.id !== id));
  };

  if (showPrintView) {
    return <A4PrintView prescription={prescription} onBack={() => setShowPrintView(false)} />;
  }

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <Header />
      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground font-semibold">Initializing clinical database...</p>
        </div>
      ) : authError ? (
        <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
          <p className="text-destructive font-bold mb-2">Backend Connection Error</p>
          <p className="text-sm text-muted-foreground max-w-sm mb-4">
            {authError}. Please ensure your backend FastAPI server is running on port 8000.
          </p>
          <Button onClick={() => window.location.reload()}>Retry Connection</Button>
        </div>
      ) : (
        <SplitLayout
          leftPanel={
            <>
              <div className="mb-2 shrink-0">
                <h2 className="font-bold text-lg mb-4 text-foreground">Exercise Library</h2>
                <SearchBar value={searchQuery} onChange={setSearchQuery} />
                <FilterChips
                  parts={allBodyPartsList}
                  selectedParts={selectedParts}
                  onToggle={togglePartFilter}
                  onApply={applyPartFilters}
                  onClear={clearPartFilters}
                  isDirty={isDirty}
                />
              </div>
              <ExerciseList
                exercises={exercises}
                addedIds={addedIds}
                onAdd={addExercise}
              />
            </>
          }
          rightPanel={
            <PrescriptionBuilder
              prescription={prescription}
              onChange={updatePrescriptionItem}
              onRemove={removeExercise}
              onGenerateReport={() => setShowPrintView(true)}
            />
          }
        />
      )}
    </div>
  );
}

