"use client"

/*
 * Landmark review step, founders' Q6, 10 October 2026.
 *
 * The clinician checks every point a measurement reads, drags any that sit
 * in the wrong place, or marks one as not visible, before a report exists.
 * The report button stays disabled until all three views have been opened,
 * and the server refuses a report without a complete review as well, so
 * this screen is not the only guard.
 *
 * Points come normalised to the photograph (0 to 1), which is why they can
 * be drawn as percentages over the image at any screen size.
 */

import { useCallback, useMemo, useRef, useState } from "react"

import type {
  DetectionResult,
  LandmarkReviewSubmission,
  ReviewedView,
} from "@/types/posture"

type ViewName = "side" | "front" | "back"

const VIEW_ORDER: ViewName[] = ["side", "front", "back"]
const VIEW_TITLE: Record<ViewName, string> = {
  side: "Side",
  front: "Front",
  back: "Back",
}

// Points the model was less sure of are ringed in orange so the clinician
// looks at them first. Founders' suggestion, 80 percent.
const LOW_CONFIDENCE = 0.8

const LOUPE_SIZE = 140
const LOUPE_ZOOM = 3
// The loupe sits above the finger so the finger does not cover the point.
const LOUPE_OFFSET_Y = 110

interface EditablePoint {
  key: string
  index: number | null // null for a pupil
  name: string
  x: number
  y: number
  lowConfidence: boolean
  notVisible: boolean
  isPupil: boolean
}

function initialPoints(detection: DetectionResult): Record<ViewName, EditablePoint[]> {
  const out = {} as Record<ViewName, EditablePoint[]>

  for (const view of VIEW_ORDER) {
    const v = detection.views[view]
    const points: EditablePoint[] = v.points.map((p) => ({
      key: `p${p.index}`,
      index: p.index,
      name: p.name,
      x: p.x,
      y: p.y,
      lowConfidence: p.visibility < LOW_CONFIDENCE,
      notVisible: false,
      isPupil: false,
    }))

    if (view === "front") {
      // If the face model found no pupils, start them on the head for the
      // clinician to place, from the pose model's nose.
      const nose = v.points.find((p) => p.index === 0)
      const pupils = v.iris ?? [
        { name: "Pupil, image left", x: (nose?.x ?? 0.5) - 0.02, y: (nose?.y ?? 0.1) - 0.01 },
        { name: "Pupil, image right", x: (nose?.x ?? 0.5) + 0.02, y: (nose?.y ?? 0.1) - 0.01 },
      ]
      pupils.forEach((q, i) =>
        points.push({
          key: `iris${i}`,
          index: null,
          name: q.name,
          x: q.x,
          y: q.y,
          lowConfidence: !v.iris,
          notVisible: false,
          isPupil: true,
        }),
      )
    }

    out[view] = points
  }

  return out
}

function toSubmission(points: Record<ViewName, EditablePoint[]>): LandmarkReviewSubmission {
  const view = (name: ViewName): ReviewedView => {
    const pts = points[name]
    const body: ReviewedView = {
      points: pts
        .filter((p) => !p.isPupil)
        .map((p) => ({ index: p.index as number, x: p.x, y: p.y, notVisible: p.notVisible })),
    }
    if (name === "front") {
      const pupils = pts.filter((p) => p.isPupil)
      const hidden = pupils.some((p) => p.notVisible)
      body.irisNotVisible = hidden
      body.iris = hidden ? null : pupils.map((p) => ({ x: p.x, y: p.y }))
    }
    return body
  }

  return { confirmed: true, side: view("side"), front: view("front"), back: view("back") }
}

interface Props {
  detection: DetectionResult
  loading: boolean
  onBack: () => void
  onConfirm: (review: LandmarkReviewSubmission) => void
}

export default function LandmarkReview({ detection, loading, onBack, onConfirm }: Props) {
  const [view, setView] = useState<ViewName>("side")
  const [visited, setVisited] = useState<Set<ViewName>>(new Set(["side"]))
  const [points, setPoints] = useState(() => initialPoints(detection))
  const [dragKey, setDragKey] = useState<string | null>(null)
  const frameRef = useRef<HTMLDivElement>(null)

  const image = detection.views[view].displayImage
  const current = points[view]
  const allVisited = VIEW_ORDER.every((v) => visited.has(v))

  const openView = (v: ViewName) => {
    setView(v)
    setVisited((prev) => new Set(prev).add(v))
    setDragKey(null)
  }

  const update = useCallback(
    (key: string, patch: Partial<EditablePoint>) => {
      setPoints((prev) => ({
        ...prev,
        [view]: prev[view].map((p) => (p.key === key ? { ...p, ...patch } : p)),
      }))
    },
    [view],
  )

  const moveTo = (key: string, clientX: number, clientY: number) => {
    const rect = frameRef.current?.getBoundingClientRect()
    if (!rect) return
    const x = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
    const y = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height))
    update(key, { x, y })
  }

  const dragging = current.find((p) => p.key === dragKey) ?? null

  const loupe = useMemo(() => {
    const rect = frameRef.current?.getBoundingClientRect()
    if (!dragging || !rect) return null
    const px = dragging.x * rect.width
    const py = dragging.y * rect.height
    return {
      left: px - LOUPE_SIZE / 2,
      top: py - LOUPE_SIZE / 2 - LOUPE_OFFSET_Y,
      backgroundSize: `${rect.width * LOUPE_ZOOM}px ${rect.height * LOUPE_ZOOM}px`,
      backgroundPosition: `${-(px * LOUPE_ZOOM - LOUPE_SIZE / 2)}px ${-(py * LOUPE_ZOOM - LOUPE_SIZE / 2)}px`,
    }
  }, [dragging])

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-8">
      <h1 className="text-2xl font-bold text-slate-900">Check the landmarks</h1>
      <p className="mt-2 max-w-2xl text-sm text-slate-600">
        Drag any point that is not on its joint. Points ringed in orange are the ones the
        model was least sure of. If a point cannot be seen in the photograph, mark it not
        visible and that measurement will be left out. Open all three views before
        confirming.
      </p>

      <div className="mt-6 flex gap-2">
        {VIEW_ORDER.map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => openView(v)}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              v === view ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700"
            }`}
          >
            {VIEW_TITLE[v]}
            {visited.has(v) ? " ✓" : ""}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        <div
          ref={frameRef}
          className="relative mx-auto w-full max-w-[420px] select-none"
          style={{ touchAction: "none" }}
          onPointerMove={(e) => dragKey && moveTo(dragKey, e.clientX, e.clientY)}
          onPointerUp={() => setDragKey(null)}
          onPointerCancel={() => setDragKey(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image} alt={`${VIEW_TITLE[view]} photograph`} className="block w-full" draggable={false} />

          {current
            .filter((p) => !p.notVisible)
            .map((p) => (
              <button
                key={p.key}
                type="button"
                aria-label={p.name}
                title={p.name}
                onPointerDown={(e) => {
                  e.currentTarget.parentElement?.setPointerCapture(e.pointerId)
                  setDragKey(p.key)
                }}
                className={`absolute h-7 w-7 -translate-x-1/2 -translate-y-1/2 rounded-full ${
                  p.lowConfidence ? "ring-4 ring-orange-400 animate-pulse" : ""
                }`}
                style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
              >
                <span
                  className={`absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white ${
                    p.isPupil ? "bg-blue-600" : "bg-emerald-500"
                  } ${p.key === dragKey ? "scale-150" : ""}`}
                />
              </button>
            ))}

          {loupe && (
            <div
              className="pointer-events-none absolute rounded-full border-4 border-white shadow-xl"
              style={{
                width: LOUPE_SIZE,
                height: LOUPE_SIZE,
                left: loupe.left,
                top: loupe.top,
                backgroundImage: `url(${image})`,
                backgroundSize: loupe.backgroundSize,
                backgroundPosition: loupe.backgroundPosition,
                backgroundRepeat: "no-repeat",
              }}
            >
              <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-red-500" />
              <span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-red-500" />
            </div>
          )}
        </div>

        <ul className="space-y-2">
          {current.map((p) => (
            <li
              key={p.key}
              className={`flex items-center justify-between rounded-xl border px-4 py-3 text-sm ${
                p.lowConfidence && !p.notVisible ? "border-orange-300 bg-orange-50" : "border-slate-200"
              }`}
            >
              <span className={p.notVisible ? "text-slate-400 line-through" : "text-slate-800"}>
                {p.name}
              </span>
              <label className="flex items-center gap-2 text-slate-600">
                <input
                  type="checkbox"
                  checked={p.notVisible}
                  onChange={(e) => {
                    const notVisible = e.target.checked
                    if (p.isPupil) {
                      // Head tilt needs both pupils, so they go together.
                      setPoints((prev) => ({
                        ...prev,
                        front: prev.front.map((q) => (q.isPupil ? { ...q, notVisible } : q)),
                      }))
                    } else {
                      update(p.key, { notVisible })
                    }
                  }}
                />
                Not visible
              </label>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={loading}
          className="rounded-full border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700"
        >
          Back to photographs
        </button>
        <button
          type="button"
          onClick={() => onConfirm(toSubmission(points))}
          disabled={!allVisited || loading}
          className="rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Generating report…" : allVisited ? "Confirm Alignment" : "Open all three views to confirm"}
        </button>
      </div>
    </section>
  )
}
