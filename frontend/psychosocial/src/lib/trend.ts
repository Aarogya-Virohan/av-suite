import type { TrendSeries } from './types';

/**
 * Layout for the score trend chart (SRS 4.1.2). Pure, so it is unit tested.
 * X is proportional to time, so 24 months of results (SRS 3.5) spread out by
 * date rather than by count. Y runs from 0 to the scale maximum.
 */
export interface TrendLayout {
  width: number;
  height: number;
  plot: { left: number; top: number; width: number; height: number };
  bands: { y: number; height: number; label: string; range: string; level: number }[];
  referralY: number | null;
  points: { x: number; y: number; score: number; date: string; band: string; referral: boolean }[];
  ticks: { x: number; date: string; anchor: 'start' | 'middle' | 'end' }[];
  showValues: boolean;
}

export const CHART = { width: 640, height: 200, left: 30, right: 130, top: 10, bottom: 26 };

export function trendLayout(series: TrendSeries, width = CHART.width, height = CHART.height): TrendLayout {
  const plot = {
    left: CHART.left,
    top: CHART.top,
    width: width - CHART.left - CHART.right,
    height: height - CHART.top - CHART.bottom,
  };
  const max = Math.max(series.max_score, 1);
  const y = (score: number) => plot.top + plot.height - (score / max) * plot.height;

  const bands = [...series.bands]
    .sort((a, b) => a.min_score - b.min_score)
    .map((b) => {
      const top = Math.max(y(b.max_score < max ? b.max_score + 1 : b.max_score), plot.top);
      const bottom = y(b.min_score);
      return { y: top, height: bottom - top, label: b.label, range: `${b.min_score}-${b.max_score}`, level: b.level };
    });

  const times = series.points.map((p) => new Date(p.completed_at).getTime());
  const t0 = Math.min(...times);
  const span = Math.max(...times) - t0;
  const x = (t: number) => (span === 0 ? plot.left + plot.width / 2 : plot.left + ((t - t0) / span) * plot.width);

  const points = series.points.map((p, i) => ({
    x: x(times[i]),
    y: y(p.score),
    score: p.score,
    date: p.completed_at,
    band: p.band_label,
    referral: p.referral,
  }));

  const n = points.length;
  let tickIdx = n > 1 ? [0, n - 1] : [0];
  if (n > 4) {
    const step = (n - 1) / 4;
    tickIdx = Array.from(new Set([0, Math.round(step), Math.round(step * 2), Math.round(step * 3), n - 1])).sort(
      (a, b) => a - b,
    );
  }
  const ticks = n === 0 ? [] : tickIdx.map((i) => ({
    x: points[i].x,
    date: points[i].date,
    anchor: (n > 1 && i === 0 ? 'start' : n > 1 && i === n - 1 ? 'end' : 'middle') as 'start' | 'middle' | 'end',
  }));

  return {
    width,
    height,
    plot,
    bands,
    referralY: series.referral_from === null ? null : y(series.referral_from),
    points,
    ticks,
    showValues: n <= 12,
  };
}

/** One sentence for screen readers, e.g. "PHQ-9: 3 results from 13 to 5, latest 5, Mild." */
export function trendSummary(series: TrendSeries): string {
  const pts = series.points;
  if (pts.length === 0) return `${series.label}: no results yet.`;
  const last = pts[pts.length - 1];
  if (pts.length === 1) return `${series.label}: one result, ${last.score}, ${last.band_label}.`;
  return `${series.label}: ${pts.length} results from ${pts[0].score} to ${last.score}, latest ${last.score}, ${last.band_label}.`;
}
