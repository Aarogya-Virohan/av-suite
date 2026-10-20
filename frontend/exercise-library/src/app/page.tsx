"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CloudOff, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { SplitLayout } from "@/components/layout/SplitLayout";
import { SearchBar } from "@/components/library/SearchBar";
import { FilterChips } from "@/components/library/FilterChips";
import { ExerciseList } from "@/components/library/ExerciseList";
import { PrescriptionBuilder } from "@/components/prescription/PrescriptionBuilder";
import { Exercise, PrescriptionItem } from "@/types/exercise";
import { fetchExercises, getToken } from "@/lib/api";

const SEARCH_DEBOUNCE_MS = 250;

export default function Home() {
  const router = useRouter();
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [selectedParts, setSelectedParts] = useState<string[]>([]);
  const [bodyParts, setBodyParts] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefetching, setIsRefetching] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const firstLoad = useRef(true);

  // Route guard.
  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  // Debounce typing so a word is one request, not one per letter.
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Fetch on search or chip change. Older requests are aborted, so a slow
  // response can never overwrite a newer one, and the current list stays on
  // screen (dimmed) until the new one arrives.
  useEffect(() => {
    if (!getToken()) return;
    const controller = new AbortController();
    const initial = firstLoad.current;
    if (initial) setIsLoading(true);
    else setIsRefetching(true);

    fetchExercises(search || undefined, selectedParts.join(",") || undefined, controller.signal)
      .then((data) => {
        setExercises(data);
        setLoadError(null);
        if (initial) {
          // Chip list comes from the unfiltered first load.
          setBodyParts(Array.from(new Set(data.map((e) => e.bodyPart))).filter(Boolean));
          firstLoad.current = false;
        }
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(err instanceof Error ? err.message : "Could not load exercises.");
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setIsLoading(false);
        setIsRefetching(false);
      });

    return () => controller.abort();
  }, [search, selectedParts, reloadKey]);

  const togglePart = (part: string) =>
    setSelectedParts((prev) => (prev.includes(part) ? prev.filter((p) => p !== part) : [...prev, part]));

  const resetFilters = () => {
    setSearchInput("");
    setSearch("");
    setSelectedParts([]);
  };

  const addedIds = useMemo(() => prescription.map((p) => p.exercise.id), [prescription]);

  const addExercise = useCallback((exercise: Exercise) => {
    setPrescription((prev) =>
      prev.some((p) => p.exercise.id === exercise.id)
        ? prev
        : [
            ...prev,
            {
              exercise,
              sets: exercise.sets,
              reps: exercise.reps,
              hold: exercise.hold,
              frequency: exercise.frequency,
            },
          ]
    );
  }, []);

  const updateItem = useCallback((updated: PrescriptionItem) => {
    setPrescription((prev) => prev.map((i) => (i.exercise.id === updated.exercise.id ? updated : i)));
  }, []);

  const removeExercise = useCallback((id: string) => {
    setPrescription((prev) => prev.filter((i) => i.exercise.id !== id));
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground lg:h-screen lg:overflow-hidden">
      <Header />
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center gap-2 text-sm font-medium text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin text-grove" />
          Loading exercises...
        </div>
      ) : loadError && exercises.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-danger-wash text-danger">
            <CloudOff className="h-5 w-5" />
          </span>
          <div>
            <p className="font-display text-lg font-bold text-ink">Exercises could not be loaded</p>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">{loadError}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              setReloadKey((k) => k + 1);
            }}
            className="h-10 cursor-pointer rounded-[10px] bg-grove px-4 text-sm font-semibold text-white shadow-primary hover:bg-grove-hover"
          >
            Try again
          </button>
        </div>
      ) : (
        <SplitLayout
          rightCount={prescription.length}
          leftPanel={
            <>
              <div className="shrink-0 space-y-3 pb-4">
                <div className="flex items-baseline justify-between">
                  <h1 className="font-display text-xl font-bold text-ink">Exercise Library</h1>
                  <span className="text-xs font-medium text-muted-foreground">
                    {exercises.length} {exercises.length === 1 ? "exercise" : "exercises"}
                  </span>
                </div>
                <SearchBar value={searchInput} onChange={setSearchInput} busy={isRefetching} />
                <FilterChips
                  parts={bodyParts}
                  selectedParts={selectedParts}
                  onToggle={togglePart}
                  onClear={() => setSelectedParts([])}
                />
                {loadError && (
                  <p role="alert" className="text-xs font-medium text-danger">
                    {loadError}
                  </p>
                )}
              </div>
              <ExerciseList
                exercises={exercises}
                addedIds={addedIds}
                onAdd={addExercise}
                stale={isRefetching}
                onReset={resetFilters}
                hasFilters={!!searchInput || selectedParts.length > 0}
              />
            </>
          }
          rightPanel={
            <PrescriptionBuilder
              prescription={prescription}
              onChange={updateItem}
              onRemove={removeExercise}
              onReplace={setPrescription}
            />
          }
        />
      )}
    </div>
  );
}
