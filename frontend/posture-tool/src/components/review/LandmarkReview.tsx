"use client"

/*
 * Landmark review step, founders' Q6, 10 October 2026. Redesigned 11 October
 * after the first phone test.
 *
 * The clinician goes through the three photographs one at a time (side,
 * front, back), drags any point that is not on its landmark, marks a point
 * not visible if it cannot be seen, and then confirms on a summary screen.
 * No report exists until "Confirm Alignment" is pressed. The server also
 * refuses an unconfirmed or incomplete review, so this screen is not the
 * only guard.
 *
 * What changed from the first version:
 * - One view at a time. The old tabs had ticks that read like "approved"
 *   when they only meant "opened".
 * - The list of every point with a checkbox is gone. Tapping a point opens
 *   its controls: not visible, reset, zoom.
 * - Zoom and pan, so the face points on the front view can be told apart.
 * - Skeleton lines, so a point off its joint shows up as a bent line.
 * - Points to check are counted, and "Check next" steps
 *   through them.
 * - A drag only starts after the finger moves a few pixels, so tapping a
 *   point to select it never nudges it.
 *
 * Points are normalised to the photograph (0 to 1). The submission sent to
 * the server is the same shape as before.
 */

import { useCallback, useEffect, useRef, useState } from "react"
import type { PointerEvent as ReactPointerEvent } from "react"

import type {
  DetectionResult,
  LandmarkReviewSubmission,
  ReviewedView,
} from "@/types/posture"

type ViewName = "side" | "front" | "back"
type Stage = ViewName | "summary"

const VIEW_ORDER: ViewName[] = ["side", "front", "back"]
const STAGES: Stage[] = ["side", "front", "back", "summary"]
const STAGE_TITLE: Record<Stage, string> = {
  side: "Side",
  front: "Front",
  back: "Back",
  summary: "Confirm",
}

const VIEW_HINT: Record<ViewName, string> = {
  // The model places joint centres, not bony landmarks: on a side photo its
  // shoulder falls toward the back of the shoulder and its hip near the
  // waistband (docs/known_limitations.md, PT-L05). The bands the founders
  // approved on 11 October rest on studies that used the acromion and the
  // greater trochanter, so the clinician is told where each point belongs.
  side:
    "Only the side facing the camera is checked. Ear point on the ear opening, shoulder on the bony tip of the shoulder, hip on the bony bump at the side of the hip, knee at the middle of the joint, ankle on the outer ankle bone.",
  front:
    "Left and right are the patient's own sides, so the left shoulder appears on the right of the photo. Pupils go in the centre of each eye.",
  // Shoulder level is defined between the acromions (founders' guidelines,
  // 10 October 2026), and on 11 October moving the back points to the bony
  // landmarks took one subject's trunk shift from 23 mm to 3 mm.
  back:
    "From behind, the head point is an estimate. Place it on the middle of the back of the head. Shoulder points on the bony tips of the shoulders, hip points on the bony bumps at the sides of the hips.",
}

// Points the model was less sure of are flagged. Founders' suggestion, 80 percent.
const LOW_CONFIDENCE = 0.8

// Points flagged for checking whatever the model's confidence, because the
// model places a joint centre where the measurement needs a bony landmark.
// Side view: documented on all seven test subjects (known_limitations.md,
// PT-L05), shoulder toward the back of the shoulder, hip near the
// waistband. Back view: on 11 October moving one shoulder point to the bony
// tip took a trunk shift from 23 mm to 3 mm. Indices are MediaPipe's.
const ALWAYS_CHECK: Record<ViewName, number[]> = {
  side: [11, 12, 23, 24],
  front: [],
  back: [11, 12, 23, 24],
}

const ZOOM = 2.6
const LOUPE = 124
const LOUPE_GAP = 92
const DRAG_THRESHOLD = 4
const NUDGE = 0.002

// MediaPipe Pose indices.
const NOSE = 0
const EDGES: Record<ViewName, [number, number][]> = {
  side: [
    [7, 11],
    [8, 12],
    [11, 23],
    [12, 24],
    [23, 25],
    [24, 26],
    [25, 27],
    [26, 28],
  ],
  front: [
    [11, 12],
    [23, 24],
    [11, 23],
    [12, 24],
    [23, 25],
    [25, 27],
    [24, 26],
    [26, 28],
  ],
  back: [
    [11, 12],
    [23, 24],
    [11, 23],
    [12, 24],
    [23, 27],
    [24, 28],
  ],
}

interface EditablePoint {
  key: string
  index: number | null // null for a pupil
  name: string
  x: number
  y: number
  origX: number
  origY: number
  lowConfidence: boolean
  // True when flagged because of the landmark problem above, rather than
  // because the model was unsure.
  jointCentre: boolean
  notVisible: boolean
  isPupil: boolean
}

type PointsByView = Record<ViewName, EditablePoint[]>

interface DragState {
  mode: "point" | "pan"
  key?: string
  sx: number
  sy: number
  ox: number
  oy: number
  moved: boolean
}

interface LoupeState {
  left: number
  top: number
  bgW: number
  bgH: number
  bgX: number
  bgY: number
  name: string
}

const clamp = (v: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v))
const clampFocus = (v: number) => clamp(v, 0.5 / ZOOM, 1 - 0.5 / ZOOM)
const isMoved = (p: EditablePoint) =>
  Math.abs(p.x - p.origX) > 1e-4 || Math.abs(p.y - p.origY) > 1e-4

function initialPoints(detection: DetectionResult): PointsByView {
  const out = {} as PointsByView

  for (const view of VIEW_ORDER) {
    const v = detection.views[view]
    const points: EditablePoint[] = v.points.map((p) => ({
      key: `p${p.index}`,
      index: p.index,
      name: p.name,
      x: p.x,
      y: p.y,
      origX: p.x,
      origY: p.y,
      lowConfidence: p.visibility < LOW_CONFIDENCE || ALWAYS_CHECK[view].includes(p.index),
      jointCentre: ALWAYS_CHECK[view].includes(p.index),
      notVisible: false,
      isPupil: false,
    }))

    if (view === "front") {
      // If the face model found no pupils, start them on the head for the
      // clinician to place, from the pose model's nose.
      const nose = v.points.find((p) => p.index === NOSE)
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
          origX: q.x,
          origY: q.y,
          lowConfidence: !v.iris,
          jointCentre: false,
          notVisible: false,
          isPupil: true,
        }),
      )
    }

    out[view] = points
  }

  return out
}

function toSubmission(points: PointsByView): LandmarkReviewSubmission {
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

/* ------------------------------------------------------------------ icons */

function IconCheck({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="none" aria-hidden>
      <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconZoom({ out = false }: { out?: boolean }) {
  return (
    <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]" fill="none" aria-hidden>
      <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M13 13l4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M6 8.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      {!out && <path d="M8.5 6v5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />}
    </svg>
  )
}

function IconReset() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" aria-hidden>
      <path d="M4 10a6 6 0 1 0 1.8-4.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M4 3.5V7h3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 animate-spin" fill="none" aria-hidden>
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.2" />
      <path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

/* -------------------------------------------------------------- overlays */

function Skeleton({ view, points }: { view: ViewName; points: EditablePoint[] }) {
  const byIndex = new Map(
    points.filter((p) => p.index !== null && !p.notVisible).map((p) => [p.index as number, p]),
  )
  const segments: [EditablePoint, EditablePoint][] = []
  for (const [a, b] of EDGES[view]) {
    const p = byIndex.get(a)
    const q = byIndex.get(b)
    if (p && q) segments.push([p, q])
  }
  if (view === "front") {
    const pupils = points.filter((p) => p.isPupil && !p.notVisible)
    if (pupils.length === 2) segments.push([pupils[0], pupils[1]])
  }

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden
    >
      {segments.map(([p, q]) => (
        <g key={`${p.key}-${q.key}`}>
          <line
            x1={p.x * 100}
            y1={p.y * 100}
            x2={q.x * 100}
            y2={q.y * 100}
            stroke="rgba(0,0,0,0.35)"
            strokeWidth={3.5}
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          <line
            x1={p.x * 100}
            y1={p.y * 100}
            x2={q.x * 100}
            y2={q.y * 100}
            stroke="rgba(255,255,255,0.85)"
            strokeWidth={1.5}
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        </g>
      ))}
    </svg>
  )
}

function Marker({
  p,
  selected,
  flagged,
  scale,
  disabled,
  onPointerDown,
}: {
  p: EditablePoint
  selected: boolean
  flagged: boolean
  scale: number
  disabled: boolean
  onPointerDown: (e: ReactPointerEvent<HTMLButtonElement>) => void
}) {
  return (
    <button
      type="button"
      aria-label={p.name}
      aria-pressed={selected}
      disabled={disabled}
      onPointerDown={onPointerDown}
      className="absolute flex h-11 w-11 items-center justify-center outline-none"
      style={{
        left: `${p.x * 100}%`,
        top: `${p.y * 100}%`,
        transform: `translate(-50%, -50%) scale(${1 / scale})`,
        touchAction: "none",
        zIndex: selected ? 3 : flagged ? 2 : 1,
      }}
    >
      {flagged && !selected && (
        <span className="absolute h-[30px] w-[30px] rounded-full border-2 border-[#E8A23A] bg-[#E8A23A]/15" />
      )}
      {selected && (
        <span className="absolute h-[34px] w-[34px] rounded-full border-2 border-white shadow-[0_0_0_2px_#1C7A54,0_2px_8px_rgba(0,0,0,0.35)]" />
      )}
      {p.notVisible ? (
        <span className="h-[14px] w-[14px] rounded-full border-2 border-dashed border-white/85" />
      ) : p.isPupil ? (
        <span className="relative h-[13px] w-[13px] rounded-full border-2 border-white shadow-[0_0_0_1px_rgba(0,0,0,0.55)]">
          <span className="absolute left-1/2 top-1/2 h-[3px] w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#FFFDF7]" />
        </span>
      ) : (
        <span className="h-[14px] w-[14px] rounded-full border-[2.5px] border-white bg-[#1C7A54] shadow-[0_1px_3px_rgba(0,0,0,0.55)]" />
      )}
    </button>
  )
}

function frameWidth(w: number, h: number, maxVh: number) {
  return `min(100%, calc(${maxVh}vh * ${w / h}))`
}

/* ------------------------------------------------------------- component */

interface Props {
  detection: DetectionResult
  loading: boolean
  onBack: () => void
  onConfirm: (review: LandmarkReviewSubmission) => void
}

export default function LandmarkReview({ detection, loading, onBack, onConfirm }: Props) {
  const [stage, setStage] = useState<Stage>("side")
  const [reached, setReached] = useState(0)
  const [points, setPoints] = useState<PointsByView>(() => initialPoints(detection))
  const [selected, setSelected] = useState<string | null>(null)
  const [seen, setSeen] = useState<Set<string>>(() => new Set())
  const [zoom, setZoom] = useState({ on: false, fx: 0.5, fy: 0.5 })
  const [dragging, setDragging] = useState(false)
  const [loupe, setLoupe] = useState<LoupeState | null>(null)

  const sectionRef = useRef<HTMLElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const innerRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const firstRender = useRef(true)

  const view: ViewName | null = stage === "summary" ? null : stage
  const stageIndex = STAGES.indexOf(stage)
  const current = view ? points[view] : []
  const scale = zoom.on ? ZOOM : 1
  const selectedPoint = current.find((p) => p.key === selected) ?? null

  const unseenFlagged = useCallback(
    (v: ViewName) =>
      points[v].filter((p) => p.lowConfidence && !p.notVisible && !seen.has(`${v}:${p.key}`)),
    [points, seen],
  )

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [stage])

  const goTo = (s: Stage) => {
    const i = STAGES.indexOf(s)
    setStage(s)
    setReached((r) => Math.max(r, i))
    setSelected(null)
    setZoom({ on: false, fx: 0.5, fy: 0.5 })
    setLoupe(null)
  }

  const update = useCallback(
    (key: string, patch: Partial<EditablePoint>) => {
      if (!view) return
      setPoints((prev) => ({
        ...prev,
        [view]: prev[view].map((p) => (p.key === key ? { ...p, ...patch } : p)),
      }))
    },
    [view],
  )

  const focusOn = (x: number, y: number) =>
    setZoom({ on: true, fx: clampFocus(x), fy: clampFocus(y) })

  const select = (key: string, focus = false) => {
    if (!view) return
    setSelected(key)
    setSeen((prev) => new Set(prev).add(`${view}:${key}`))
    if (focus) {
      const p = points[view].find((q) => q.key === key)
      if (p) focusOn(p.x, p.y)
    }
  }

  const setNotVisible = (p: EditablePoint, notVisible: boolean) => {
    if (p.isPupil) {
      // Head tilt needs both pupils, so they go together.
      setPoints((prev) => ({
        ...prev,
        front: prev.front.map((q) => (q.isPupil ? { ...q, notVisible } : q)),
      }))
    } else {
      update(p.key, { notVisible })
    }
  }

  const toggleZoom = () => {
    if (zoom.on) {
      setZoom((z) => ({ ...z, on: false }))
      return
    }
    const nose = current.find((p) => p.index === NOSE)
    const target = selectedPoint ?? (view === "front" ? nose : null)
    if (target) focusOn(target.x, target.y)
    else focusOn(0.5, 0.5)
  }

  const checkNext = () => {
    if (!view) return
    const next = unseenFlagged(view)[0]
    if (next) select(next.key, true)
  }

  /* ---- pointer handling ---- */

  const onMarkerDown = (p: EditablePoint) => (e: ReactPointerEvent<HTMLButtonElement>) => {
    if (loading) return
    e.stopPropagation()
    e.preventDefault()
    frameRef.current?.setPointerCapture(e.pointerId)
    dragRef.current = { mode: "point", key: p.key, sx: e.clientX, sy: e.clientY, ox: p.x, oy: p.y, moved: false }
    select(p.key)
  }

  const onFrameDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (loading) return
    dragRef.current = { mode: "pan", sx: e.clientX, sy: e.clientY, ox: zoom.fx, oy: zoom.fy, moved: false }
    if (zoom.on) frameRef.current?.setPointerCapture(e.pointerId)
  }

  const onFrameMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const d = dragRef.current
    const inner = innerRef.current
    const wrap = wrapRef.current
    if (!d || !inner || !wrap) return

    const dx = e.clientX - d.sx
    const dy = e.clientY - d.sy
    if (!d.moved) {
      if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return
      if (d.mode === "pan" && !zoom.on) {
        // Not zoomed: a background drag is a page scroll, not ours.
        dragRef.current = null
        return
      }
      d.moved = true
      setDragging(true)
      if (d.mode === "point" && typeof navigator !== "undefined" && "vibrate" in navigator) {
        navigator.vibrate(8)
      }
    }

    const rect = inner.getBoundingClientRect()

    if (d.mode === "point" && d.key) {
      const x = clamp(d.ox + dx / rect.width)
      const y = clamp(d.oy + dy / rect.height)
      update(d.key, { x, y })

      const w = wrap.getBoundingClientRect()
      const px = rect.left - w.left + x * rect.width
      const py = rect.top - w.top + y * rect.height
      const lz = zoom.on ? 1.6 : 2.5
      let left = clamp(px - LOUPE / 2, 0, Math.max(0, w.width - LOUPE))
      let top = py - LOUPE / 2 - LOUPE_GAP
      if (top < -LOUPE / 3) {
        // No room above: put the loupe beside the finger instead.
        top = py - LOUPE / 2
        left = px > w.width / 2 ? px - LOUPE - 52 : px + 52
      }
      const name = current.find((q) => q.key === d.key)?.name ?? ""
      setLoupe({
        left,
        top,
        bgW: rect.width * lz,
        bgH: rect.height * lz,
        bgX: -(x * rect.width * lz - LOUPE / 2),
        bgY: -(y * rect.height * lz - LOUPE / 2),
        name,
      })
    } else if (d.mode === "pan") {
      setZoom((z) => ({
        ...z,
        fx: clampFocus(d.ox - dx / rect.width),
        fy: clampFocus(d.oy - dy / rect.height),
      }))
    }
  }

  const endDrag = (deselectOnTap: boolean) => {
    const d = dragRef.current
    dragRef.current = null
    setDragging(false)
    setLoupe(null)
    if (deselectOnTap && d && d.mode === "pan" && !d.moved) setSelected(null)
  }

  /* ---- keyboard nudge ---- */

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!view || !selected) return
      const p = points[view].find((q) => q.key === selected)
      if (!p) return
      const step = e.shiftKey ? NUDGE * 5 : NUDGE
      let dx = 0
      let dy = 0
      switch (e.key) {
        case "ArrowLeft":
          dx = -step
          break
        case "ArrowRight":
          dx = step
          break
        case "ArrowUp":
          dy = -step
          break
        case "ArrowDown":
          dy = step
          break
        case "Escape":
          setSelected(null)
          return
        default:
          return
      }
      e.preventDefault()
      update(selected, { x: clamp(p.x + dx), y: clamp(p.y + dy) })
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [view, selected, points, update])

  /* ---- layout pieces ---- */

  const shift = (f: number) => clamp(0.5 - f * scale, 1 - scale, 0)
  const innerTransform = zoom.on
    ? `translate(${shift(zoom.fx) * 100}%, ${shift(zoom.fy) * 100}%) scale(${scale})`
    : "none"

  const nextStage = STAGES[stageIndex + 1]
  const prevStage = STAGES[stageIndex - 1]

  const stats = (v: ViewName) => {
    const pts = points[v]
    return {
      moved: pts.filter(isMoved).length,
      hidden: pts.filter((p) => p.notVisible).map((p) => p.name),
      unseen: unseenFlagged(v).length,
    }
  }

  const flaggedLeft = view ? unseenFlagged(view).length : 0
  const totalUnseen = VIEW_ORDER.reduce((n, v) => n + stats(v).unseen, 0)

  return (
    <section
      ref={sectionRef}
      className="mx-auto w-full max-w-3xl scroll-mt-4 pb-28 sm:pb-0"
    >
      {/* Stepper */}
      <ol className="flex items-center gap-1.5" aria-label="Review progress">
        {STAGES.map((s, i) => {
          // A view is done once it has been opened. "Confirm" is never shown
          // as done, because nothing is confirmed until the button is pressed.
          const done = s !== "summary" && i <= reached && i !== stageIndex
          const active = i === stageIndex
          const reachable = i <= reached && !loading
          return (
            <li key={s} className="flex flex-1 items-center gap-1.5 last:flex-none">
              <button
                type="button"
                disabled={!reachable}
                onClick={() => goTo(s)}
                aria-current={active ? "step" : undefined}
                className={`flex flex-none items-center gap-2 rounded-full p-1 text-[13px] font-medium transition sm:pr-3 ${active ? "pr-3" : ""} ${
                  active
                    ? "bg-[#0B1238] text-white"
                    : reachable
                      ? "text-[#141A33] hover:bg-[#EDE6D6]"
                      : "text-[#8B90A8]"
                }`}
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-[12px] tabular-nums ${
                    active
                      ? "bg-[#FFFDF7] text-[#141A33]"
                      : done
                        ? "bg-[#1C7A54] text-white"
                        : "border border-[#D9D1BF] bg-[#FFFDF7]"
                  }`}
                >
                  {done && !active ? <IconCheck className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <span className={active ? "" : "hidden sm:inline"}>{STAGE_TITLE[s]}</span>
              </button>
              {i < STAGES.length - 1 && <span className="h-px flex-1 bg-[#E3DCCB]" />}
            </li>
          )
        })}
      </ol>

      {view ? (
        <>
          <header className="mt-6">
            <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[#5D6380]">
              Landmark check · {stageIndex + 1} of 3
            </p>
            <h1 className="mt-1 font-display text-[26px] font-extrabold leading-tight tracking-tight text-[#141A33]">
              {STAGE_TITLE[view]} view
            </h1>
            <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-[#5D6380]">
              Drag any point that is off its landmark. Tap a point for more options.
            </p>
          </header>

          {/* Photograph */}
          <div className="mt-5 rounded-2xl bg-[#0B1238] p-2 sm:p-3">
            <div className="mb-2 flex items-center justify-between gap-3 pl-2">
              <p className="text-[12px] text-white/60">
                {zoom.on ? "Drag the photo to look around" : `${current.length} points`}
              </p>
              <button
                type="button"
                onClick={toggleZoom}
                className="flex h-9 flex-none items-center gap-1.5 rounded-full bg-white/10 px-3 text-[13px] font-medium text-white transition hover:bg-white/20"
              >
                <IconZoom out={zoom.on} />
                {zoom.on ? "Fit" : view === "front" && !selectedPoint ? "Zoom to face" : "Zoom"}
              </button>
            </div>
            <div ref={wrapRef} className="relative mx-auto" style={{ width: frameWidth(detection.views[view].widthPx, detection.views[view].heightPx, 66) }}>
              <div
                ref={frameRef}
                className="relative w-full select-none overflow-hidden rounded-xl"
                style={{
                  aspectRatio: `${detection.views[view].widthPx} / ${detection.views[view].heightPx}`,
                  touchAction: zoom.on ? "none" : "pan-y",
                  cursor: zoom.on ? (dragging ? "grabbing" : "grab") : "default",
                }}
                onPointerDown={onFrameDown}
                onPointerMove={onFrameMove}
                onPointerUp={() => endDrag(true)}
                onPointerCancel={() => endDrag(false)}
              >
                <div
                  ref={innerRef}
                  className="absolute inset-0 origin-top-left"
                  style={{
                    transform: innerTransform,
                    transition: dragging ? "none" : "transform 280ms cubic-bezier(0.2, 0.8, 0.2, 1)",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={detection.views[view].displayImage}
                    alt={`${STAGE_TITLE[view]} photograph`}
                    className="absolute inset-0 h-full w-full"
                    draggable={false}
                  />
                  <Skeleton view={view} points={current} />
                  {current.map((p) => (
                    <Marker
                      key={p.key}
                      p={p}
                      selected={p.key === selected}
                      flagged={p.lowConfidence && !p.notVisible && !seen.has(`${view}:${p.key}`)}
                      scale={scale}
                      disabled={loading}
                      onPointerDown={onMarkerDown(p)}
                    />
                  ))}
                </div>

              </div>

              {loupe && (
                <div
                  className="pointer-events-none absolute z-20"
                  style={{ left: loupe.left, top: loupe.top, width: LOUPE }}
                >
                  <div
                    className="relative overflow-hidden rounded-full border-[3px] border-white bg-black shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
                    style={{
                      width: LOUPE,
                      height: LOUPE,
                      backgroundImage: `url(${detection.views[view].displayImage})`,
                      backgroundSize: `${loupe.bgW}px ${loupe.bgH}px`,
                      backgroundPosition: `${loupe.bgX}px ${loupe.bgY}px`,
                      backgroundRepeat: "no-repeat",
                    }}
                  >
                    <span className="absolute left-1/2 top-[18%] h-[22%] w-px -translate-x-1/2 bg-white/90" />
                    <span className="absolute bottom-[18%] left-1/2 h-[22%] w-px -translate-x-1/2 bg-white/90" />
                    <span className="absolute left-[18%] top-1/2 h-px w-[22%] -translate-y-1/2 bg-white/90" />
                    <span className="absolute right-[18%] top-1/2 h-px w-[22%] -translate-y-1/2 bg-white/90" />
                    <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#1C7A54] ring-2 ring-white" />
                  </div>
                  <p className="mt-1.5 truncate rounded-full bg-black/70 px-2 py-0.5 text-center text-[11px] font-medium text-white">
                    {loupe.name}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Context panel: selected point, or the view's guidance */}
          <div className="mt-4 min-h-[112px]">
            {selectedPoint ? (
              <div className="rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[16px] font-semibold text-[#141A33]">{selectedPoint.name}</p>
                    <p className="mt-0.5 text-[13px] text-[#5D6380]">
                      {selectedPoint.notVisible
                        ? "Not visible. Measurements that need it are left out."
                        : isMoved(selectedPoint)
                          ? "Moved from where the model placed it."
                          : selectedPoint.jointCentre
                            ? "The model marks the joint centre here, not the bone. Move it onto the bony landmark."
                            : selectedPoint.lowConfidence
                              ? "The model was unsure of this one. Check it closely."
                            : "Where the model placed it."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelected(null)}
                    className="flex-none rounded-full px-2 py-1 text-[13px] font-medium text-[#5D6380] hover:bg-[#F1EFEA]"
                  >
                    Done
                  </button>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setNotVisible(selectedPoint, !selectedPoint.notVisible)}
                    role="switch"
                    aria-checked={selectedPoint.notVisible}
                    className={`flex h-11 items-center justify-center gap-2 rounded-xl border text-[13px] font-medium transition ${
                      selectedPoint.notVisible
                        ? "border-[#0B1238] bg-[#0B1238] text-white"
                        : "border-[#E3DCCB] text-[#141A33] hover:bg-[#F3EEE2]"
                    }`}
                  >
                    <span
                      className={`relative h-4 w-7 rounded-full transition ${
                        selectedPoint.notVisible ? "bg-white/30" : "bg-[#D9D1BF]"
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-3 w-3 rounded-full bg-[#FFFDF7] transition-all ${
                          selectedPoint.notVisible ? "left-3.5" : "left-0.5"
                        }`}
                      />
                    </span>
                    Not visible
                  </button>
                  <button
                    type="button"
                    disabled={!isMoved(selectedPoint)}
                    onClick={() => update(selectedPoint.key, { x: selectedPoint.origX, y: selectedPoint.origY })}
                    className="flex h-11 items-center justify-center gap-1.5 rounded-xl border border-[#E3DCCB] text-[13px] font-medium text-[#141A33] transition hover:bg-[#F3EEE2] disabled:opacity-35"
                  >
                    <IconReset />
                    Reset
                  </button>
                  <button
                    type="button"
                    onClick={() => focusOn(selectedPoint.x, selectedPoint.y)}
                    className="flex h-11 items-center justify-center gap-1.5 rounded-xl border border-[#E3DCCB] text-[13px] font-medium text-[#141A33] transition hover:bg-[#F3EEE2]"
                  >
                    <IconZoom />
                    Zoom here
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2.5">
                {flaggedLeft > 0 && (
                  <div className="flex items-center gap-3 rounded-2xl border border-[#F0D9B5] bg-[#FBF3E6] p-3 pl-4">
                    <span className="h-2.5 w-2.5 flex-none rounded-full border-2 border-[#E8A23A]" />
                    <p className="flex-1 text-[14px] text-[#6B4A12]">
                      {flaggedLeft === 1
                        ? "1 point to check"
                        : `${flaggedLeft} points to check`}
                    </p>
                    <button
                      type="button"
                      onClick={checkNext}
                      className="h-9 flex-none rounded-full bg-[#4E888F] px-4 text-[13px] font-semibold text-white hover:bg-[#3B6A70]"
                    >
                      Check next
                    </button>
                  </div>
                )}
                <p className="px-1 text-[14px] leading-relaxed text-[#5D6380]">{VIEW_HINT[view]}</p>
              </div>
            )}
          </div>

          {/* Point chips */}
          <div className="mt-3">
            <p className="mb-2 px-1 text-[12px] font-medium uppercase tracking-[0.12em] text-[#5D6380]">
              Points
            </p>
            <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0 [scrollbar-width:none]">
              {current.map((p) => {
                const flagged = p.lowConfidence && !p.notVisible && !seen.has(`${view}:${p.key}`)
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => select(p.key, zoom.on)}
                    className={`flex h-9 flex-none items-center gap-2 rounded-full border px-3 text-[13px] transition ${
                      p.key === selected
                        ? "border-[#0B1238] bg-[#0B1238] text-white"
                        : flagged
                          ? "border-[#F0D9B5] bg-[#FBF3E6] text-[#6B4A12]"
                          : "border-[#E3DCCB] bg-[#FFFDF7] text-[#141A33] hover:bg-[#F3EEE2]"
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${
                        p.notVisible
                          ? "border border-dashed border-current"
                          : isMoved(p)
                            ? "bg-[#1C7A54] ring-2 ring-[#1C7A54]/25"
                            : flagged
                              ? "border-2 border-[#E8A23A]"
                              : "bg-current opacity-40"
                      }`}
                    />
                    <span className={p.notVisible ? "line-through opacity-60" : ""}>{p.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      ) : (
        /* Summary */
        <>
          <header className="mt-6">
            <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[#5D6380]">
              Landmark check · last step
            </p>
            <h1 className="mt-1 font-display text-[26px] font-extrabold leading-tight tracking-tight text-[#141A33]">
              Confirm the landmarks
            </h1>
            <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-[#5D6380]">
              The report is calculated only from these points. Tap a view to change anything.
            </p>
          </header>

          <div className="mt-5 grid grid-cols-3 gap-2.5 sm:gap-4">
            {VIEW_ORDER.map((v) => {
              const s = stats(v)
              const d = detection.views[v]
              return (
                <button
                  key={v}
                  type="button"
                  disabled={loading}
                  onClick={() => goTo(v)}
                  className="group overflow-hidden rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] text-left transition hover:border-[#C9C0AA]"
                >
                  <div className="bg-[#0B1238] p-1.5">
                    <div
                      className="relative mx-auto overflow-hidden rounded-lg"
                      style={{ width: frameWidth(d.widthPx, d.heightPx, 34), aspectRatio: `${d.widthPx} / ${d.heightPx}` }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={d.displayImage} alt="" className="absolute inset-0 h-full w-full" draggable={false} />
                      <Skeleton view={v} points={points[v]} />
                      {points[v]
                        .filter((p) => !p.notVisible)
                        .map((p) => (
                          <span
                            key={p.key}
                            className={`absolute h-[7px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white ${
                              p.isPupil ? "bg-transparent" : "bg-[#1C7A54]"
                            }`}
                            style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
                          />
                        ))}
                    </div>
                  </div>
                  <div className="p-2.5 sm:p-3">
                    <p className="flex items-center justify-between text-[14px] font-semibold text-[#141A33]">
                      {STAGE_TITLE[v]}
                      <span className="text-[12px] font-medium text-[#1C7A54] opacity-0 transition group-hover:opacity-100">
                        Edit
                      </span>
                    </p>
                    <p className="mt-0.5 text-[12px] leading-snug text-[#5D6380]">
                      {s.moved === 0 && s.hidden.length === 0
                        ? "As detected"
                        : [
                            s.moved ? `${s.moved} moved` : null,
                            s.hidden.length ? `${s.hidden.length} not visible` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                    </p>
                    {s.unseen > 0 && (
                      <p className="mt-1 text-[12px] font-medium text-[#A8670F]">
                        {s.unseen} unchecked
                      </p>
                    )}
                  </div>
                </button>
              )
            })}
          </div>

          {(VIEW_ORDER.some((v) => stats(v).hidden.length > 0) || totalUnseen > 0) && (
            <div className="mt-4 space-y-2 rounded-2xl border border-[#E3DCCB] bg-[#FFFDF7] p-4 text-[14px]">
              {VIEW_ORDER.map((v) => {
                const hidden = stats(v).hidden
                if (!hidden.length) return null
                return (
                  <p key={v} className="text-[#454B66]">
                    <span className="font-medium text-[#141A33]">{STAGE_TITLE[v]}, not visible:</span>{" "}
                    {hidden.join(", ")}. Measurements that need these are left out.
                  </p>
                )
              })}
              {totalUnseen > 0 && (
                <p className="text-[#A8670F]">
                  {totalUnseen === 1
                    ? "1 point marked for checking has not been opened."
                    : `${totalUnseen} points marked for checking have not been opened.`}{" "}
                  You can still confirm if they look right.
                </p>
              )}
            </div>
          )}

          <p className="mt-4 px-1 text-[13px] leading-relaxed text-[#5D6380]">
            By confirming, you are stating that these points sit on the patient&apos;s landmarks.
          </p>
        </>
      )}

      {/* Actions: sticky on phones, inline on larger screens */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-[#E3DCCB] bg-[#FFFDF7]/95 px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-md sm:static sm:mt-8 sm:border-0 sm:bg-transparent sm:p-0 sm:backdrop-blur-none">
        <div className="mx-auto flex max-w-3xl gap-3">
          <button
            type="button"
            disabled={loading}
            onClick={() => (prevStage ? goTo(prevStage) : onBack())}
            className="h-12 flex-none rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-5 text-[15px] font-medium text-[#141A33] transition hover:bg-[#F3EEE2] disabled:opacity-40"
          >
            {prevStage ? "Back" : "Retake photos"}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => (nextStage ? goTo(nextStage) : onConfirm(toSubmission(points)))}
            className="flex h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-[#4E888F] px-5 text-[15px] font-semibold text-white transition hover:bg-[#3B6A70] disabled:opacity-60"
          >
            {loading ? (
              <>
                <Spinner />
                Building report
              </>
            ) : nextStage === "summary" ? (
              "Review and confirm"
            ) : nextStage ? (
              `Next: ${STAGE_TITLE[nextStage]} view`
            ) : (
              "Confirm Alignment"
            )}
          </button>
        </div>
      </div>
    </section>
  )
}
