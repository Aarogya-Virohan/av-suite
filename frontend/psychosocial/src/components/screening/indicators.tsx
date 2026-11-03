import { AlertOctagon, AlertTriangle, CheckCircle2, CircleDot, Flag, Info, ShieldAlert } from 'lucide-react';
import { Badge, type BadgeTone } from '@/components/ui/brand';
import { cn } from '@/lib/cn';
import { bandCount, toneFor, type SeverityTone } from '@/lib/severity';
import type { AssignmentStatus, InstrumentId, Scale, SessionStatus } from '@/lib/types';

const TONE_TEXT: Record<SeverityTone, string> = {
  ok: 'text-ok',
  info: 'text-info',
  warn: 'text-warn',
  danger: 'text-danger',
};

const TONE_WASH: Record<SeverityTone, string> = {
  ok: 'bg-ok-wash',
  info: 'bg-info-wash',
  warn: 'bg-warn-wash',
  danger: 'bg-danger-wash',
};

const TONE_ICON = {
  ok: CheckCircle2,
  info: CircleDot,
  warn: AlertTriangle,
  danger: AlertOctagon,
} as const;

/**
 * Severity for one scale: band label, an icon that changes with severity,
 * and a segmented meter where the number of filled segments is the band.
 * Readable without colour.
 */
export function SeverityIndicator({
  instrumentId,
  scale,
  size = 'md',
}: {
  instrumentId: InstrumentId;
  scale: Scale;
  size?: 'sm' | 'md';
}) {
  const tone = toneFor(scale.band_level, scale.referral);
  const Icon = TONE_ICON[tone];
  const count = bandCount(instrumentId, scale.scale_id);
  const label = `${scale.band_label}, band ${scale.band_level + 1} of ${count}`;

  if (size === 'sm') {
    return (
      <span className={cn('inline-flex items-center gap-1.5 text-[13px] font-semibold', TONE_TEXT[tone])}>
        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="tabular-nums">{scale.score}</span>
        <span className="text-ink-2">{scale.band_label}</span>
      </span>
    );
  }

  return (
    <div className="space-y-2">
      <div className={cn('flex items-center gap-2 font-semibold', TONE_TEXT[tone])}>
        <span className={cn('grid h-7 w-7 place-items-center rounded-lg', TONE_WASH[tone])}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="text-[15px]">{scale.band_label}</span>
      </div>
      <div
        className={cn('flex gap-1', TONE_TEXT[tone])}
        role="img"
        aria-label={label}
      >
        {Array.from({ length: count }, (_, i) => (
          <span key={i} className="sev-seg" data-on={i <= scale.band_level} />
        ))}
      </div>
    </div>
  );
}

const SESSION_STATUS: Record<SessionStatus, { label: string; tone: BadgeTone }> = {
  pending: { label: 'Awaiting patient', tone: 'neutral' },
  in_progress: { label: 'In progress', tone: 'info' },
  completed: { label: 'Completed', tone: 'ok' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
};

export function SessionStatusBadge({
  status,
  linkStatus,
}: {
  status: SessionStatus;
  linkStatus?: AssignmentStatus;
}) {
  if (linkStatus === 'expired' && status !== 'completed') {
    return <Badge tone="warn">Link expired</Badge>;
  }
  const s = SESSION_STATUS[status];
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

export function FlagChips({
  referral,
  risk,
  partialRisk,
}: {
  referral: boolean;
  risk: boolean;
  partialRisk?: boolean;
}) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {risk || partialRisk ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-danger px-2 py-0.5 text-xs font-semibold text-white">
          <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
          {partialRisk && !risk ? 'Risk answer (not submitted)' : 'Risk answer'}
        </span>
      ) : null}
      {referral ? (
        <span className="inline-flex items-center gap-1 rounded-full border border-danger/40 bg-danger-wash px-2 py-0.5 text-xs font-semibold text-danger">
          <Flag className="h-3.5 w-3.5" aria-hidden="true" />
          Referral suggested
        </span>
      ) : null}
    </span>
  );
}

export function RiskBanner({
  answerLabel,
  submitted,
}: {
  answerLabel: string | null;
  submitted: boolean;
}) {
  return (
    <div
      role="alert"
      className="flex gap-3 rounded-2xl border border-danger/40 bg-danger-wash p-4 text-danger sm:p-5"
    >
      <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <div className="space-y-1 text-sm">
        <p className="font-display text-[15px] font-bold">
          Thoughts of self-harm reported{submitted ? '' : ' (questionnaire not yet submitted)'}
        </p>
        <p className="text-ink-2">
          PHQ-9 question 9, &ldquo;Thoughts that you would be better off dead or of hurting yourself in some
          way&rdquo;, was answered{answerLabel ? <> &ldquo;{answerLabel}&rdquo;</> : ' above Not at all'}. This
          is flagged whatever the total score. Follow your clinic&apos;s safety procedure and speak with the
          patient directly.
        </p>
      </div>
    </div>
  );
}

export function InfoNote({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn('flex gap-2 text-xs text-muted', className)}>
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: React.ElementType;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line bg-card/60 px-6 py-12 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-xl bg-grove-wash text-grove">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <p className="mt-3 font-display text-[15px] font-bold text-ink">{title}</p>
      {children ? <div className="mt-1 max-w-sm text-sm text-muted">{children}</div> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function NoAccess({ what }: { what: string }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-8 text-center shadow-card">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-xl bg-warn-wash text-warn">
        <ShieldAlert className="h-5 w-5" aria-hidden="true" />
      </span>
      <p className="mt-3 font-display text-[15px] font-bold text-ink">You don&apos;t have access to {what}</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
        Ask a clinic admin to grant it from the Access page. Individual screening results are visible only to
        treating physiotherapists.
      </p>
    </div>
  );
}
