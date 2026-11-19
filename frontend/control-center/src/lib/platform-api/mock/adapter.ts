import type { PlatformApi, TokenProvider } from '../api';
import { isPlatformApiError } from '../errors';
import { MockPlatformBackend, type MockBackendState } from './backend';

const DEFAULT_LATENCY_MS = 250;
const STORAGE_KEY = 'av-control-center.mock-state';

function loadState(): MockBackendState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as MockBackendState) : null;
  } catch {
    return null;
  }
}

function saveState(backend: MockPlatformBackend): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(backend.exportState()));
  } catch {
    // Storage full or blocked: the mock keeps working for this page only.
  }
}

interface MockAdapterOptions {
  latencyMs?: number;
  backend?: MockPlatformBackend;
  /** Same hook as the HTTP adapter: called on every 401. */
  onUnauthorized?: () => void;
  /** Keep mock data across reloads (sessionStorage). Off in tests. */
  persist?: boolean;
}

/**
 * Wraps the mock backend with network-like latency, persistence across
 * reloads, the same 401 handling as the HTTP adapter, and copies every
 * response so screens cannot change mock state by accident.
 */
export function createMockPlatformApi(getToken: TokenProvider, options: MockAdapterOptions = {}): PlatformApi {
  const persist = options.persist ?? true;
  const backend = options.backend ?? new MockPlatformBackend({ state: persist ? loadState() : null });
  const latency = options.latencyMs ?? DEFAULT_LATENCY_MS;
  const inner = backend.api(getToken);
  const wait = () => (latency > 0 ? new Promise((resolve) => setTimeout(resolve, latency)) : Promise.resolve());

  return new Proxy(inner, {
    get(target, property: keyof PlatformApi) {
      const method = target[property];
      if (typeof method !== 'function') return method;
      return async (...args: unknown[]) => {
        await wait();
        try {
          const result = await (method as (...a: unknown[]) => Promise<unknown>)(...args);
          return structuredClone(result);
        } catch (error) {
          if (isPlatformApiError(error) && error.status === 401) options.onUnauthorized?.();
          throw error;
        } finally {
          if (persist) saveState(backend);
        }
      };
    },
  });
}
