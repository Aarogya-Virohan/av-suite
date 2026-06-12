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
import exerciseData from "@/data/exercises.json";

export default function Home() {
  const [exercises] = useState<Exercise[]>(exerciseData as Exercise[]);
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  
  const [showPrintView, setShowPrintView] = useState(false);

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
            onGenerateReport={() => setShowPrintView(true)}
          />
        }
      />
    </div>
  );
}
