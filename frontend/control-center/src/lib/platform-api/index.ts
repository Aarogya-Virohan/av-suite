import type { PlatformApi } from './api';
import { createHttpPlatformApi } from './http';
import { createMockPlatformApi } from './mock/adapter';
import { getAccessToken, handleUnauthorized } from '@/store/session';

export type PlatformApiMode = 'mock' | 'http';

/**
 * "mock" or "http" from NEXT_PUBLIC_PLATFORM_API_MODE. When unset, production
 * builds use the real API and development uses the mock, so a deploy can
 * never show mock data unless someone asked for it.
 */
export function resolveApiMode(): PlatformApiMode {
  const value = process.env.NEXT_PUBLIC_PLATFORM_API_MODE;
  if (value === 'mock' || value === 'http') return value;
  return process.env.NODE_ENV === 'production' ? 'http' : 'mock';
}

export const API_MODE: PlatformApiMode = resolveApiMode();

let instance: PlatformApi | null = null;

/** The single PlatformApi used by every screen (through features/<x>/hooks). */
export function platformApi(): PlatformApi {
  if (!instance) {
    instance =
      API_MODE === 'mock'
        ? createMockPlatformApi(getAccessToken)
        : createHttpPlatformApi(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000', getAccessToken, handleUnauthorized);
  }
  return instance;
}

export type { PlatformApi } from './api';
export * from './errors';
export * from './types';
