import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/cn';

/*
 * Shared brand primitives for the AV Suite CRM.
 * Colours come from the @theme tokens in app/globals.css, never raw hex,
 * so a palette change happens in one place.
 */

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-2xl border border-line bg-card shadow-card', className)}
      {...props}
    />
  );
}

export function CardHeader({
  title,
  action,
  className,
}: {
  title: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('mb-3 flex items-center justify-between gap-3', className)}>
      <h2 className="font-display text-[15.5px] font-bold text-ink">{title}</h2>
      {action}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-[26px] font-bold tracking-tight text-ink">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2.5">{actions}</div> : null}
    </div>
  );
}

const iconChipVariants = cva('grid h-9 w-9 shrink-0 place-items-center rounded-[10px]', {
  variants: {
    tone: {
      grove: 'bg-grove-wash text-grove',
      teal: 'bg-logo-teal-wash text-logo-teal',
      info: 'bg-info-wash text-info',
      warn: 'bg-warn-wash text-warn',
      danger: 'bg-danger-wash text-danger',
      hero: 'bg-white/10 text-lime',
    },
  },
  defaultVariants: { tone: 'grove' },
});

export type IconTone = NonNullable<VariantProps<typeof iconChipVariants>['tone']>;

export function IconChip({
  icon: Icon,
  tone,
}: {
  icon: React.ElementType;
  tone?: IconTone;
}) {
  return (
    <span className={iconChipVariants({ tone })}>
      <Icon className="h-[18px] w-[18px]" strokeWidth={1.8} aria-hidden="true" />
    </span>
  );
}

/**
 * KPI tile. `hero` is the single midnight card per page that carries the
 * brand gradient; every other KPI is a plain card.
 */
export function KpiCard({
  label,
  value,
  icon,
  tone = 'grove',
  hero = false,
  footer,
  className,
}: {
  label: string;
  value: React.ReactNode;
  icon: React.ElementType;
  tone?: IconTone;
  hero?: boolean;
  footer?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl p-5',
        hero
          ? 'bg-[radial-gradient(90%_120%_at_100%_0%,#1d5a5a_0%,rgba(29,90,90,0)_55%),linear-gradient(135deg,#0b1238_0%,#13235a_60%,#1b4a54_100%)] text-white shadow-hero'
          : 'border border-line bg-card shadow-card',
        className,
      )}
    >
      {hero ? (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br from-fresh to-[#0b665a] opacity-50"
        />
      ) : null}
      <div className="relative flex items-center justify-between">
        <span className={cn('text-[12.5px] font-medium', hero ? 'text-[#b9c0e0]' : 'text-muted')}>
          {label}
        </span>
        <IconChip icon={icon} tone={hero ? 'hero' : tone} />
      </div>
      <p
        className={cn(
          'relative mt-3 font-display text-[30px] font-bold leading-none tracking-tight tabular-nums',
          hero ? 'text-white' : 'text-ink',
        )}
      >
        {value}
      </p>
      {footer ? <div className="relative mt-3 text-xs">{footer}</div> : null}
    </div>
  );
}

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full py-0.5 pl-2 pr-2.5 text-xs font-semibold before:h-1.5 before:w-1.5 before:rounded-full before:bg-current',
  {
    variants: {
      tone: {
        ok: 'bg-ok-wash text-ok',
        info: 'bg-info-wash text-info',
        warn: 'bg-warn-wash text-warn',
        danger: 'bg-danger-wash text-danger',
        active: 'bg-logo-teal-wash text-logo-teal-ink',
        neutral: 'bg-slate-100 text-slate-600',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
);

export type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>['tone']>;

export function Badge({
  tone,
  children,
  className,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={cn(badgeVariants({ tone }), className)}>{children}</span>;
}

export const buttonVariants = cva(
  'inline-flex h-10 items-center justify-center gap-2 rounded-[10px] px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'border border-grove-hover bg-gradient-to-b from-[#22895f] to-grove text-white shadow-primary hover:from-grove hover:to-grove-hover',
        secondary: 'border border-line bg-card text-ink hover:border-slate-300 hover:bg-white',
        ghost: 'text-ink-2 hover:bg-slate-100',
      },
    },
    defaultVariants: { variant: 'primary' },
  },
);

export function Button({
  variant,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant }), className)} {...props} />;
}

/** Initials avatar with a tone taken from the brand palette. */
const AVATAR_TONES = [
  'bg-grove-wash text-ok',
  'bg-info-wash text-info',
  'bg-logo-teal-wash text-logo-teal-ink',
  'bg-warn-wash text-warn',
  'bg-danger-wash text-danger',
];

export function initialsOf(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.replace(/^dr\.?\s+/i, '').trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}

export function Avatar({
  name,
  size = 32,
  className,
}: {
  name: string | null | undefined;
  size?: number;
  className?: string;
}) {
  const initials = initialsOf(name);
  const tone = AVATAR_TONES[(initials.charCodeAt(0) + (initials.charCodeAt(1) || 0)) % AVATAR_TONES.length];
  return (
    <span
      className={cn('grid shrink-0 place-items-center rounded-full font-bold', tone, className)}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}

export function Delta({
  children,
  tone = 'ok',
  hero = false,
}: {
  children: React.ReactNode;
  tone?: 'ok' | 'warn' | 'danger' | 'active';
  hero?: boolean;
}) {
  const tones = {
    ok: 'bg-ok-wash text-ok',
    warn: 'bg-warn-wash text-warn',
    danger: 'bg-danger-wash text-danger',
    active: 'bg-logo-teal-wash text-logo-teal-ink',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold',
        hero ? 'bg-lime/15 text-lime' : tones[tone],
      )}
    >
      {children}
    </span>
  );
}

/** Segmented tab group (pill style). Used by Appointments, Billing and other sub-views. */
export function SegmentGroup({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('inline-flex flex-wrap items-center gap-1 rounded-xl bg-slate-100 p-1', className)}
      {...props}
    />
  );
}

export function SegmentTab({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'flex cursor-pointer items-center gap-2 rounded-[9px] px-3.5 py-2 text-[13px] font-semibold transition-colors',
        active ? 'bg-card text-ink shadow-[0_1px_2px_rgba(20,26,51,0.08)]' : 'text-muted hover:text-ink',
      )}
    >
      <Icon className={cn('h-4 w-4', active && 'text-grove')} />
      {children}
    </button>
  );
}
