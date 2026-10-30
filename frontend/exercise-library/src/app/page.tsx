"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CloudOff, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { SplitLayout } from "@/components/layout/SplitLayout";
import { SearchBar } from "@/components/library/SearchBar";
import { CategoryFilter } from "@/components/library/CategoryFilter";
import { ExerciseList } from "@/components/library/ExerciseList";
import { PhotoDialog } from "@/components/library/PhotoDialog";
import { CategoryEditDialog } from "@/components/library/CategoryEditDialog";
import { PrescriptionBuilder } from "@/components/prescription/PrescriptionBuilder";
import { Exercise, ExercisePhoto, PrescriptionItem } from "@/types/exercise";
import { can, fetchCategories, fetchExercises, fetchMe, getToken, type CategoryGroup } from "@/lib/api";

const SEARCH_DEBOUNCE_MS = 250;
const PAGE_SIZE = 30;

export default function Home() {
  const router = useRouter();
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [categoryGroups, setCategoryGroups] = useState<CategoryGroup[]>([]);
  const [categoriesFailed, setCategoriesFailed] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefetching, setIsRefetching] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const firstLoad = useRef(true);
  // Bumped on every new search/filter; a page that arrives for an older
  // query is dropped instead of being appended to the new list.
  const queryVersion = useRef(0);
  // Clinic photos: who may add them, and which exercise is open.
  const [canEditPhotos, setCanEditPhotos] = useState(false);
  const [photoExerciseId, setPhotoExerciseId] = useState<string | null>(null);
  // Categories of the clinic's own exercises (EL-L-10, EL-D-008).
  const [categoryExerciseId, setCategoryExerciseId] = useState<string | null>(null);
  const [categoriesKey, setCategoriesKey] = useState(0);
  const moreController = useRef<AbortController | null>(null);

  // Route guard.
  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    if (!getToken()) return;
    fetchMe()
      .then((me) => setCanEditPhotos(can(me, "exercises.edit")))
      .catch(() => setCanEditPhotos(false));
  }, []);

  const updatePhotos = useCallback((exerciseId: string, photos: ExercisePhoto[]) => {
    setExercises((prev) => prev.map((e) => (e.id === exerciseId ? { ...e, photos } : e)));
  }, []);
  const photoExercise = exercises.find((e) => e.id === photoExerciseId) ?? null;
  const categoryExercise = exercises.find((e) => e.id === categoryExerciseId) ?? null;
  const replaceExercise = useCallback((updated: Exercise) => {
    setExercises((prev) => prev.map((e) => (e.id === updated.id ? { ...updated, photos: e.photos } : e)));
    setCategoriesKey((k) => k + 1); // counts in the filter panel
  }, []);

  // Debounce typing so a word is one request, not one per letter.
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Category groups for the filter panel, with counts, from the backend.
  useEffect(() => {
    if (!getToken()) return;
    fetchCategories()
      .then((rows) => {
        setCategoryGroups(rows);
        setCategoriesFailed(false);
      })
      .catch(() => setCategoriesFailed(true));
  }, [reloadKey, categoriesKey]);

  // First page on search or filter change. Older requests are aborted, so a
  // slow response can never overwrite a newer one, and the current list stays
  // on screen (dimmed) until the new one arrives.
  useEffect(() => {
    if (!getToken()) return;
    const controller = new AbortController();
    const version = ++queryVersion.current;
    moreController.current?.abort();
    const initial = firstLoad.current;
    if (initial) setIsLoading(true);
    else setIsRefetching(true);

    fetchExercises({ search: search || undefined, categories: selectedCategories, page: 1, pageSize: PAGE_SIZE }, controller.signal)
      .then(({ items, total: count }) => {
        if (version !== queryVersion.current) return;
        setExercises(items);
        setTotal(count);
        setPage(1);
        setLoadMoreError(null);
        setLoadError(null);
        firstLoad.current = false;
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
  }, [search, selectedCategories, reloadKey]);

  const hasMore = exercises.length < total;

  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore || isRefetching) return;
    const version = queryVersion.current;
    const controller = new AbortController();
    moreController.current = controller;
    setLoadingMore(true);
    setLoadMoreError(null);
    fetchExercises(
      { search: search || undefined, categories: selectedCategories, page: page + 1, pageSize: PAGE_SIZE },
      controller.signal
    )
      .then(({ items, total: count }) => {
        if (version !== queryVersion.current) return;
        setExercises((prev) => {
          // The backend order is total (region, title, id), so pages do not
          // overlap; the id check only guards against data changing between
          // two page requests.
          const seen = new Set(prev.map((e) => e.id));
          return [...prev, ...items.filter((e) => !seen.has(e.id))];
        });
        setTotal(count);
        setPage((p) => p + 1);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (version === queryVersion.current) {
          setLoadMoreError(err instanceof Error ? err.message : "Could not load more exercises.");
        }
      })
      .finally(() => {
        if (version === queryVersion.current) setLoadingMore(false);
      });
  }, [loadingMore, hasMore, isRefetching, search, selectedCategories, page]);

  // Keep picked categories in panel order (group, then value).
  const setCategories = (next: string[]) => {
    const order = new Map(categoryGroups.flatMap((g) => g.values).map((v, i) => [v.id, i]));
    setSelectedCategories([...next].sort((a, b) => (order.get(a) ?? 1e9) - (order.get(b) ?? 1e9)));
  };

  const resetFilters = () => {
    setSearchInput("");
    setSearch("");
    setSelectedCategories([]);
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
                    {total} {total === 1 ? "exercise" : "exercises"}
                  </span>
                </div>
                <SearchBar value={searchInput} onChange={setSearchInput} busy={isRefetching} />
                <CategoryFilter
                  groups={categoryGroups}
                  selected={selectedCategories}
                  onChange={setCategories}
                  total={total}
                  unavailable={categoriesFailed}
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
                hasFilters={!!searchInput || selectedCategories.length > 0}
                hasMore={hasMore}
                loadingMore={loadingMore}
                loadMoreError={loadMoreError}
                onLoadMore={loadMore}
                onEditPhotos={canEditPhotos ? (e) => setPhotoExerciseId(e.id) : undefined}
                onEditCategories={canEditPhotos ? (e) => setCategoryExerciseId(e.id) : undefined}
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
      {categoryExercise && (
        <CategoryEditDialog
          exercise={categoryExercise}
          groups={categoryGroups}
          onClose={() => setCategoryExerciseId(null)}
          onSaved={replaceExercise}
        />
      )}
      {photoExercise && (
        <PhotoDialog
          exercise={photoExercise}
          onClose={() => setPhotoExerciseId(null)}
          onPhotosChange={updatePhotos}
        />
      )}
    </div>
  );
}
