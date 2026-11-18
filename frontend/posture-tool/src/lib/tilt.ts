// Phone tilt at capture, 27 October 2026.
//
// The capture screen used to refuse a photograph until the phone was within
// 1.5 degrees of level. By hand that was close to impossible, and a phone
// accelerometer carries a fixed offset of its own (about 1 degree on a
// typical part, 5 on a bad one), so it was also less exact than it looked.
// Now the screen only asks for a steady, roughly upright phone; the exact
// side tilt is measured here and the backend turns the reviewed points back
// by it before measuring (backend/app/services/posture/level.py).
//
// Everything here is pure, so it can be checked without a phone.

export type Gravity = { x: number; y: number; z: number }

// What travels with a captured photograph to the report.
export type CaptureLevel = { degrees: number; calibrated: boolean }

// rate: how fast the phone is turning, deg/s, from the gyroscope; null when
// the device does not report it.
export type TiltSample = { t: number; roll: number; pitch: number; rate: number | null }

// The capture screen accepts up to this much tilt either way; the backend
// refuses anything over 15.
export const MAX_TILT_DEG = 10

// 27 October 2026, first phone test: a limit on the fastest reading in the
// window (3 deg/s) flickered on and off by hand, because single readings of
// natural hand tremor cross it. The screen now uses the mean turning speed
// over STEADY_RATE_WINDOW_MS with two thresholds (hysteresis): steady once
// the mean drops to STEADY_RATE_ENTER, unsteady only when it rises past
// STEADY_RATE_LEAVE. Starting values; the ?debug=1 panel shows the real
// numbers on a phone.
export const STEADY_RATE_WINDOW_MS = 400
// Raised from 6 and 10 after the second phone test, where a phone being
// handled read 8 to 30 deg/s and the screen still could not settle.
export const STEADY_RATE_ENTER = 9
export const STEADY_RATE_LEAVE = 15

// Mean turning speed over the window, deg/s; null when the device reports no
// rotation rate or there are too few readings.
export function meanRate(samples: TiltSample[], now: number, windowMs = STEADY_RATE_WINDOW_MS): number | null {
  const w = recent(samples, now, windowMs)
  if (w.length < 5 || w.some((s) => s.rate === null)) return null
  return mean(w.map((s) => s.rate as number))
}

// Earlier rule, kept as the fallback for devices without a gyroscope:
// Steady: over the last STEADY_WINDOW_MS the phone turned no faster than
// STEADY_RATE_DEG_S (gyroscope). The gyroscope is used for this, not the
// spread of the tilt readings, because the accelerometer also feels the
// hand's small movements as noise, and a spread limit tight enough to mean
// "still" would rarely be met by hand. The tilt itself is then the mean of
// the window, which averages that noise down. Devices without a gyroscope
// fall back to the spread of the readings, more loosely.
// Starting values, to be confirmed on real phones.
export const STEADY_WINDOW_MS = 500
export const STEADY_RATE_DEG_S = 3
export const STEADY_ROLL_SPAN_DEG = 1.5
export const STEADY_PITCH_SPAN_DEG = 2
const STEADY_MIN_SAMPLES = 5

const deg = (r: number) => (r * 180) / Math.PI

// iOS (WebKit) reports accelerationIncludingGravity with every axis negated
// compared with the W3C example and Android: upright, iOS reads y near -9.8
// and Android +9.8 (W3C public-geolocation list, 2014; still so in 2026).
// A phone held upright always has gravity mostly along y, so the sign of y
// tells which convention this device uses. Only valid while upright.
export function platformSign(g: Gravity): 1 | -1 {
  return g.y >= 0 ? 1 : -1
}

export function normalise(g: Gravity, sign: 1 | -1): Gravity {
  return { x: g.x * sign, y: g.y * sign, z: g.z * sign }
}

// Side tilt as the correction the photograph needs, in degrees, positive
// meaning "turn the photo counterclockwise as seen on screen". In the W3C
// frame (x right, y up the screen) a phone turned counterclockwise by t
// reads x = g sin t, y = g cos t, and its picture shows the scene turned
// clockwise by t, so the correction is +t. Pitch (leaning toward or away)
// does not change this angle, because it scales x and y alike.
export function rollFromGravity(g: Gravity): number {
  return deg(Math.atan2(g.x, g.y))
}

// Forward or backward lean from upright, size only.
export function pitchFromGravity(g: Gravity): number {
  return Math.abs(pitchSignedFromGravity(g))
}

// The same with its direction, on a normalised reading. In the W3C frame z
// points out of the screen, so z > 0 means the screen faces partly upward:
// the top of the phone leans away from the user and the camera points down.
export function pitchSignedFromGravity(g: Gravity): number {
  return deg(Math.atan2(g.z, Math.hypot(g.x, g.y)))
}

export function wrap180(a: number): number {
  let v = ((a + 180) % 360 + 360) % 360 - 180
  if (v === -180) v = 180
  return v
}

// Reversal calibration. The phone stands on its bottom edge on any flat
// surface (r1), then upside down on its top edge in the same spot (r2).
// The surface's own slope a turns with the phone and the phone's offset b
// does not: r1 = a + b, r2 = a - b (r2 measured as the upside-down roll
// minus 180). So b = (r1 - r2) / 2, whatever the surface.
export function rollUpsideDown(g: Gravity): number {
  return wrap180(rollFromGravity(g) - 180)
}

export function biasFromReversal(r1: number, r2: number): number {
  return (r1 - r2) / 2
}

export function mean(values: number[]): number {
  return values.reduce((s, v) => s + v, 0) / values.length
}

// Overall turning speed from DeviceMotionEvent.rotationRate (deg/s).
export function rotationSpeed(r: { alpha: number | null; beta: number | null; gamma: number | null } | null): number | null {
  if (!r || r.alpha === null || r.beta === null || r.gamma === null) return null
  return Math.hypot(r.alpha, r.beta, r.gamma)
}

export function recent(samples: TiltSample[], now: number, windowMs = STEADY_WINDOW_MS): TiltSample[] {
  return samples.filter((s) => now - s.t <= windowMs)
}

export function isSteady(samples: TiltSample[], now: number): boolean {
  const w = recent(samples, now)
  if (w.length < STEADY_MIN_SAMPLES) return false
  if (w.every((s) => s.rate !== null)) {
    return Math.max(...w.map((s) => s.rate as number)) <= STEADY_RATE_DEG_S
  }
  const rolls = w.map((s) => s.roll)
  const pitches = w.map((s) => s.pitch)
  return (
    Math.max(...rolls) - Math.min(...rolls) <= STEADY_ROLL_SPAN_DEG &&
    Math.max(...pitches) - Math.min(...pitches) <= STEADY_PITCH_SPAN_DEG
  )
}

// ---- calibration storage ----
// Per phone, per browser. localStorage can be missing or throw (private
// mode, blocked storage); then the phone is simply uncalibrated.

const CAL_KEY = "av-posture-tilt-calibration-v1"

export type Calibration = { biasDeg: number; sign: 1 | -1; at: string }

export function loadCalibration(): Calibration | null {
  try {
    const raw = window.localStorage.getItem(CAL_KEY)
    if (!raw) return null
    const c = JSON.parse(raw) as Calibration
    if (typeof c.biasDeg !== "number" || !Number.isFinite(c.biasDeg) || Math.abs(c.biasDeg) > 10) return null
    if (c.sign !== 1 && c.sign !== -1) return null
    return c
  } catch {
    return null
  }
}

export function saveCalibration(c: Calibration): boolean {
  try {
    window.localStorage.setItem(CAL_KEY, JSON.stringify(c))
    return true
  } catch {
    return false
  }
}
