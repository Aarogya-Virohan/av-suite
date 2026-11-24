import type { PlatformApi } from './api';
import { createHttpPlatformApi } from './http';
import { getAccessToken, handleUnauthorized } from '@/store/session';

export type PlatformApiMode = 'mock' | 'http';

/**
 * Which data source a build uses.
 *
 * - NEXT_PUBLIC_PLATFORM_API_MODE=mock  -> mock (the only way to get mock data in a production build)
 * - NEXT_PUBLIC_PLATFORM_API_MODE=http  -> real API
 * - unset or anything else              -> real API in production, mock in development / tests
 *
 * Pure so it can be tested; the build itself relies on the inlined check in
 * loadMockApi() below, which keeps mock code out of production bundles.
 */
export function resolveApiMode(value: string | undefined, nodeEnv: string | undefined): PlatformApiMode {
  if (value === 'mock' || value === 'http') return value;
  return nodeEnv === 'production' ? 'http' : 'mock';
}

export const API_MODE: PlatformApiMode = resolveApiMode(process.env.NEXT_PUBLIC_PLATFORM_API_MODE, process.env.NODE_ENV);

/**
 * Base URL of the backend (no /api/v1). Development falls back to the usual
 * local port. A production build never guesses: no value = every call fails
 * with a clear message.
 */
export function resolveApiBaseUrl(value: string | undefined, nodeEnv: string | undefined): string | null {
  const text = (value ?? '').trim();
  if (/^https?:\/\/[^\s/]+/i.test(text)) return text.replace(/\/+$/, '');
  return nodeEnv === 'production' ? null : 'http://localhost:8000';
}

/**
 * The mock is imported only behind a check on build-time constants. In a
 * production build without NEXT_PUBLIC_PLATFORM_API_MODE=mock the condition is
 * false at compile time, so the mock adapter, its seed data and its demo
 * operators are not in the bundle at all (checked by scripts/check-bundle.mjs).
 */
async function loadMockApi(): Promise<PlatformApi> {
  if (process.env.NEXT_PUBLIC_PLATFORM_API_MODE === 'mock' || process.env.NODE_ENV !== 'production') {
    const { createMockPlatformApi } = await import('./mock/adapter');
    return createMockPlatformApi(getAccessToken, { onUnauthorized: handleUnauthorized });
  }
  throw new Error('Mock data is not available in this build.');
}

type Method = (...args: unknown[]) => Promise<unknown>;

/** A PlatformApi that loads its adapter on first use, so callers stay synchronous. */
function lazyApi(load: () => Promise<PlatformApi>): PlatformApi {
  let loaded: Promise<PlatformApi> | null = null;
  const get = () => (loaded ??= load());
  return new Proxy({} as PlatformApi, {
    get: (_target, key) => {
      if (typeof key !== 'string' || key === 'then') return undefined;
      return (...args: unknown[]) => get().then((api) => (api as unknown as Record<string, Method>)[key](...args));
    },
  });
}

let instance: PlatformApi | null = null;

/** The single PlatformApi used by every screen (through features/<x>/hooks). */
export function platformApi(): PlatformApi {
  if (!instance) {
    instance =
      API_MODE === 'mock'
        ? lazyApi(loadMockApi)
        : createHttpPlatformApi(resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_URL, process.env.NODE_ENV), getAccessToken, handleUnauthorized);
  }
  return instance;
}

export type { PlatformApi } from './api';
export * from './errors';
export * from './types';
