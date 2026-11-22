/**
 * AV Suite hub (HUB-1). Same file in crm, posture-tool, exercise-library and
 * psychosocial; keep the copies identical.
 *
 * Hub mode = this app is built with NEXT_PUBLIC_BASE_PATH (/crm, /posture,
 * /exercises, /screening) and served from one origin through the CRM
 * project's rewrites. Same origin + the same localStorage key "token" means
 * one login for every tool; the login page lives in the CRM (/crm/login).
 *
 * Without NEXT_PUBLIC_BASE_PATH (today's prod) every app behaves as before:
 * own URL, own /login. Links to the other tools then come from
 * NEXT_PUBLIC_{CRM,POSTURE,EXERCISE,SCREENING}_APP_URL (POSTURE and
 * EXERCISE already exist in the CRM's Vercel env) (fallback plan: separate
 * URLs, same credentials, links from the CRM).
 */

export type ToolKey = 'crm' | 'posture' | 'exercises' | 'screening';

export const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '');
export const HUB_MODE = BASE_PATH !== '';
/** Optional absolute hub origin, so a tool opened on its own deployment URL still finds the common login. */
const HUB_ORIGIN = (process.env.NEXT_PUBLIC_HUB_ORIGIN || '').replace(/\/+$/, '');

export const HUB_PATHS: Record<ToolKey, string> = {
  crm: '/crm',
  posture: '/posture',
  exercises: '/exercises',
  screening: '/screening',
};

// Literal process.env reads so Next inlines them at build time.
const STANDALONE_URLS: Record<ToolKey, string | undefined> = {
  crm: process.env.NEXT_PUBLIC_CRM_APP_URL,
  posture: process.env.NEXT_PUBLIC_POSTURE_APP_URL,
  exercises: process.env.NEXT_PUBLIC_EXERCISE_APP_URL,
  screening: process.env.NEXT_PUBLIC_SCREENING_APP_URL,
};

/** Tools mounted on the hub origin (comma list; default all). */
const HUB_TOOLS = (process.env.NEXT_PUBLIC_HUB_TOOLS || 'crm,posture,exercises,screening')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

/** A file from /public, with the base path in front ("/brand/x.png"). */
export function asset(path: string): string {
  return `${BASE_PATH}${path}`;
}

/** Where a tool lives, or null when this build has no address for it. */
export function toolUrl(key: ToolKey): string | null {
  if (HUB_MODE) return HUB_TOOLS.includes(key) ? HUB_PATHS[key] : null;
  const url = STANDALONE_URLS[key];
  return url ? url.replace(/\/+$/, '') : null;
}

/**
 * Only a same-origin path inside the hub may follow the login page.
 * Returns null for anything else (other origins, "//x", "/\\x").
 */
export function safeHubNext(value: string | null | undefined): string | null {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return null;
  const ok = Object.values(HUB_PATHS).some((p) => value === p || value.startsWith(`${p}/`) || value.startsWith(`${p}?`));
  return ok ? value : null;
}

/**
 * The login page address. Hub mode: the common AV Suite login in the CRM,
 * with ?next= set to where the user was. Standalone: this app's own /login
 * (path without base path; callers using router add it themselves).
 */
export function hubLoginUrl(opts: { next?: string | null; expired?: boolean } = {}): string | null {
  if (!HUB_MODE) return null;
  const params = new URLSearchParams();
  if (opts.expired) params.set('expired', '1');
  const next = safeHubNext(opts.next ?? null);
  if (next && !next.startsWith(`${HUB_PATHS.crm}/login`)) params.set('next', next);
  const q = params.toString();
  const path = `${HUB_PATHS.crm}/login${q ? `?${q}` : ''}`;
  if (HUB_ORIGIN && typeof window !== 'undefined' && window.location.origin !== HUB_ORIGIN) return `${HUB_ORIGIN}${path}`;
  return path;
}

/** Current address (with base path) for ?next=. */
export function currentPath(): string {
  if (typeof window === 'undefined') return '';
  return `${window.location.pathname}${window.location.search}`;
}

/**
 * Hub mode: full page load to the common login and return true.
 * Standalone: do nothing and return false (the app uses its own /login).
 */
export function redirectToHubLogin(opts: { expired?: boolean; keepNext?: boolean } = {}): boolean {
  const url = hubLoginUrl({ expired: opts.expired, next: opts.keepNext === false ? null : currentPath() });
  if (!url || typeof window === 'undefined') return false;
  window.location.replace(url);
  return true;
}
