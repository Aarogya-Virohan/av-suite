import type { PlatformApi, TokenProvider } from '../api';
import { MockPlatformBackend } from './backend';

const DEFAULT_LATENCY_MS = 250;

/**
 * Wraps the mock backend with network-like latency and copies every
 * response, so screens cannot mutate mock state by accident.
 */
export function createMockPlatformApi(getToken: TokenProvider, options: { latencyMs?: number; backend?: MockPlatformBackend } = {}): PlatformApi {
  const backend = options.backend ?? new MockPlatformBackend();
  const latency = options.latencyMs ?? DEFAULT_LATENCY_MS;
  const inner = backend.api(getToken);
  const wait = () => (latency > 0 ? new Promise((resolve) => setTimeout(resolve, latency)) : Promise.resolve());

  return new Proxy(inner, {
    get(target, property: keyof PlatformApi) {
      const method = target[property];
      if (typeof method !== 'function') return method;
      return async (...args: unknown[]) => {
        await wait();
        const result = await (method as (...a: unknown[]) => Promise<unknown>)(...args);
        return structuredClone(result);
      };
    },
  });
}
