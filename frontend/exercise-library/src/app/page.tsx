"use client";

import React, { useState, useMemo } from "react";
import { Header } from "@/components/layout/Header";
import { SplitLayout } from "@/components/layout/SplitLayout";
import { SearchBar } from "@/components/library/SearchBar";
import { FilterChips } from "@/components/library/FilterChips";
import { ExerciseList } from "@/components/library/ExerciseList";
import { PrescriptionBuilder } from "@/components/prescription/PrescriptionBuilder";
import { A4PrintView } from "@/components/report/A4PrintView";

import { Exercise, PrescriptionItem } from "@/types/exercise";
import { useQuery } from "@tanstack/react-query";
import { fetchExercises, login, savePrescription, generatePdf } from "@/lib/api";

export default function Home() {
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  
  const [showPrintView, setShowPrintView] = useState(false);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  
  // Login on mount automatically for dev
  React.useEffect(() => {
    login().catch(console.error);
  }, []);

  const { data: exercises = [], isLoading } = useQuery<Exercise[]>({
    queryKey: ["exercises"],
    queryFn: () => fetchExercises()
  });

  // Derived state for filtering
  const allBodyParts = useMemo(() => {
    const parts = new Set(exercises.map(e => e.bodyPart));
    return Array.from(parts);
  }, [exercises]);

  const filteredExercises = useMemo(() => {
    return exercises.filter((ex) => {
      const matchesSearch =
        ex.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ex.condition.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesPart = selectedPart ? ex.bodyPart === selectedPart : true;
      return matchesSearch && matchesPart;
    });
  }, [exercises, searchQuery, selectedPart]);

  const addedIds = useMemo(() => prescription.map(p => p.exercise.id), [prescription]);

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
    <div className="flex flex-col min-h-screen">
      <Header />
      <SplitLayout
        leftPanel={
          <>
            <div className="mb-2 shrink-0">
              <h2 className="font-bold text-lg mb-4">Exercise Library</h2>
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
              <FilterChips
                parts={allBodyParts}
                selectedPart={selectedPart}
                onSelect={setSelectedPart}
              />
            </div>
            <ExerciseList
              exercises={filteredExercises}
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
            onGenerateReport={async () => {
              try {
                // 1. Save Prescription to backend
                const saved = await savePrescription(prescription);
                // 2. Generate PDF
                const pdfUrl = await generatePdf(saved.id);
                setGeneratedPdfUrl(pdfUrl);
                window.open(`http://localhost:8000${pdfUrl}`, '_blank');
              } catch (e) {
                console.error("Error generating report", e);
                // Fallback
                setShowPrintView(true);
              }
            }}
          />
        }
      />
    </div>
  );
}
