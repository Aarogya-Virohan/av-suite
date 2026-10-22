'use client';

import { formatDate } from '@/lib/format';
import { trendLayout, trendSummary } from '@/lib/trend';
import type { TrendSeries } from '@/lib/types';
import { Card } from '@/components/ui/brand';

// Lightest tint for the lowest band. Bands are also named on the right,
// so colour is never the only cue (SRS 3.6).
const TINTS = [
  'var(--color-card)',
  'var(--color-warn-wash)',
  '#f3e3c9',
  '#f0d0bd',
  'var(--color-danger-wash)',
];

export function TrendChart({ series }: { series: TrendSeries }) {
  const L = trendLayout(series);
  const n = series.points.length;
  const summary = trendSummary(series);

  return (
    <Card className="min-w-0 p-4">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-ink">{series.label}</p>
        <p className="text-xs text-muted">
          {n} result{n === 1 ? '' : 's'} · score 0 to {series.max_score}
        </p>
      </div>
      {/* Below about 520 px the labels get too small to read, so the chart
          keeps a minimum width and scrolls inside its card on phones. */}
      <div className="-mx-1 overflow-x-auto px-1">
        <svg
          viewBox={`0 0 ${L.width} ${L.height}`}
          className="h-auto w-full min-w-[520px]"
          role="img"
          aria-label={summary}
          style={{ fontFamily: 'inherit' }}
        >
          {L.bands.map((b) => (
            <g key={b.label}>
              <rect
                x={L.plot.left}
                y={b.y}
                width={L.plot.width}
                height={b.height}
                fill={TINTS[Math.min(b.level, TINTS.length - 1)]}
                stroke="var(--color-line)"
                strokeWidth={0.6}
              />
              <text x={L.plot.left + L.plot.width + 6} y={b.y + b.height / 2 + 3.5} fontSize={10} fill="var(--color-muted)">
                {b.label} ({b.range})
              </text>
            </g>
          ))}
          {[0, series.max_score].map((v) => (
            <text
              key={v}
              x={L.plot.left - 5}
              y={L.plot.top + L.plot.height - (v / Math.max(series.max_score, 1)) * L.plot.height + 3.5}
              fontSize={10}
              textAnchor="end"
              fill="var(--color-muted)"
            >
              {v}
            </text>
          ))}
          {L.referralY !== null ? (
            <g>
              <line
                x1={L.plot.left}
                x2={L.plot.left + L.plot.width}
                y1={L.referralY}
                y2={L.referralY}
                stroke="var(--color-danger)"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
              <text
                x={L.plot.left + L.plot.width - 4}
                y={L.referralY - 4}
                fontSize={9.5}
                textAnchor="end"
                fill="var(--color-danger)"
              >
                Referral from {series.referral_from}
              </text>
            </g>
          ) : null}
          {L.points.length > 1 ? (
            <polyline
              points={L.points.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="var(--color-midnight)"
              strokeWidth={1.8}
            />
          ) : null}
          {L.points.map((p, i) => (
            <g key={`${p.date}-${i}`}>
              <circle cx={p.x} cy={p.y} r={4} fill={p.referral ? 'var(--color-danger)' : 'var(--color-midnight)'}>
                <title>{`${formatDate(p.date)}: ${p.score}, ${p.band}`}</title>
              </circle>
              {L.showValues ? (
                <text x={p.x} y={p.y - 8} fontSize={10.5} fontWeight={700} textAnchor="middle" fill="var(--color-ink)">
                  {p.score}
                </text>
              ) : null}
            </g>
          ))}
          {L.ticks.map((t) => (
            <text key={`${t.date}-${t.x}`} x={t.x} y={L.height - 8} fontSize={10} textAnchor={t.anchor} fill="var(--color-muted)">
              {formatDate(t.date)}
            </text>
          ))}
        </svg>
      </div>
      {n === 1 ? <p className="mt-1 text-xs text-muted">One result so far. The trend shows from the second result.</p> : null}
      <table className="sr-only">
        <caption>{series.label} results</caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>Score</th>
            <th>Band</th>
          </tr>
        </thead>
        <tbody>
          {series.points.map((p) => (
            <tr key={p.session_id}>
              <td>{formatDate(p.completed_at)}</td>
              <td>{p.score}</td>
              <td>{p.band_label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
