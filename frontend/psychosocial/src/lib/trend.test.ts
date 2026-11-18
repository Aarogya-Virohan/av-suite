import { describe, expect, it } from 'vitest';
import { CHART, trendLayout, trendSummary } from './trend';
import type { TrendSeries } from './types';

const phq: Omit<TrendSeries, 'points'> = {
  instrument_id: 'phq9',
  short_name: 'PHQ-9',
  scale_id: 'total',
  label: 'PHQ-9',
  max_score: 27,
  referral_from: 10,
  bands: [
    { min_score: 0, max_score: 4, label: 'None-minimal', level: 0 },
    { min_score: 5, max_score: 9, label: 'Mild', level: 1 },
    { min_score: 10, max_score: 14, label: 'Moderate', level: 2 },
    { min_score: 15, max_score: 19, label: 'Moderately severe', level: 3 },
    { min_score: 20, max_score: 27, label: 'Severe', level: 4 },
  ],
};

const point = (date: string, score: number) => ({
  session_id: date,
  completed_at: date,
  score,
  band_label: 'x',
  band_level: 0,
  referral: score >= 10,
});

describe('trendLayout', () => {
  it('places points by date and score inside the plot', () => {
    const L = trendLayout({ ...phq, points: [point('2026-01-01T00:00:00Z', 0), point('2026-01-11T00:00:00Z', 27), point('2026-01-31T00:00:00Z', 9)] });
    const right = L.plot.left + L.plot.width;
    const bottom = L.plot.top + L.plot.height;
    expect(L.points[0]).toMatchObject({ x: L.plot.left, y: bottom });
    expect(L.points[1].y).toBe(L.plot.top);
    expect(L.points[2].x).toBe(right);
    // 10 of 30 days in: one third of the width, proportional to time not count.
    expect(L.points[1].x).toBeCloseTo(L.plot.left + L.plot.width / 3, 5);
    expect(L.referralY).toBeCloseTo(bottom - (10 / 27) * L.plot.height, 5);
  });

  it('stacks bands without gaps from 0 to the maximum', () => {
    const L = trendLayout({ ...phq, points: [point('2026-01-01T00:00:00Z', 5)] });
    const bottom = L.plot.top + L.plot.height;
    expect(L.bands[0].y + L.bands[0].height).toBeCloseTo(bottom, 5);
    for (let i = 1; i < L.bands.length; i++) {
      expect(L.bands[i].y + L.bands[i].height).toBeCloseTo(L.bands[i - 1].y, 5);
    }
    expect(L.bands[L.bands.length - 1].y).toBeCloseTo(L.plot.top, 5);
    // A single result sits in the middle.
    expect(L.points[0].x).toBe(L.plot.left + L.plot.width / 2);
  });

  it('handles 24 monthly results with at most five date labels and no value labels', () => {
    const pts = Array.from({ length: 24 }, (_, i) => point(new Date(Date.UTC(2024, 10 + i, 5)).toISOString(), (i * 7) % 28));
    const L = trendLayout({ ...phq, points: pts });
    expect(L.points).toHaveLength(24);
    expect(L.ticks.length).toBeLessThanOrEqual(5);
    expect(L.ticks[0].anchor).toBe('start');
    expect(L.ticks[L.ticks.length - 1].anchor).toBe('end');
    expect(L.showValues).toBe(false);
    for (const p of L.points) {
      expect(p.x).toBeGreaterThanOrEqual(L.plot.left);
      expect(p.x).toBeLessThanOrEqual(CHART.width - CHART.right);
      expect(p.y).toBeGreaterThanOrEqual(L.plot.top);
      expect(p.y).toBeLessThanOrEqual(L.plot.top + L.plot.height);
    }
  });
});

describe('trendSummary', () => {
  it('reads the trend in words', () => {
    const two = { ...phq, points: [{ ...point('2026-01-01T00:00:00Z', 13), band_label: 'Moderate' }, { ...point('2026-02-01T00:00:00Z', 5), band_label: 'Mild' }] };
    expect(trendSummary(two)).toBe('PHQ-9: 2 results from 13 to 5, latest 5, Mild.');
    expect(trendSummary({ ...phq, points: [two.points[1]] })).toBe('PHQ-9: one result, 5, Mild.');
  });
});
