import { afterEach, describe, expect, it, vi } from 'vitest';

async function load(env: Record<string, string>) {
  vi.resetModules();
  for (const [k, v] of Object.entries(env)) vi.stubEnv(k, v);
  return import('./hub');
}

afterEach(() => vi.unstubAllEnvs());

describe('hub helpers (HUB-1)', () => {
  it('standalone: no base path, no hub login', async () => {
    const h = await load({ NEXT_PUBLIC_BASE_PATH: '' });
    expect(h.HUB_MODE).toBe(false);
    expect(h.asset('/brand/x.png')).toBe('/brand/x.png');
    expect(h.hubLoginUrl({ next: '/posture' })).toBeNull();
  });

  it('hub mode: assets and login go through the base paths', async () => {
    const h = await load({ NEXT_PUBLIC_BASE_PATH: '/posture/' });
    expect(h.asset('/brand/x.png')).toBe('/posture/brand/x.png');
    expect(h.hubLoginUrl({ next: '/posture/analyze?patient_id=1', expired: true })).toBe(
      '/crm/login?expired=1&next=%2Fposture%2Fanalyze%3Fpatient_id%3D1',
    );
  });

  it('next only accepts hub paths on the same origin', async () => {
    const h = await load({ NEXT_PUBLIC_BASE_PATH: '/crm' });
    expect(h.safeHubNext('/exercises')).toBe('/exercises');
    expect(h.safeHubNext('/screening/sessions')).toBe('/screening/sessions');
    expect(h.safeHubNext('//evil.com/crm')).toBeNull();
    expect(h.safeHubNext('/\\evil.com')).toBeNull();
    expect(h.safeHubNext('https://evil.com/crm')).toBeNull();
    expect(h.safeHubNext('/crmx')).toBeNull();
    expect(h.safeHubNext('/admin')).toBeNull();
    // no login loop
    expect(h.hubLoginUrl({ next: '/crm/login?next=/x' })).toBe('/crm/login');
  });
});
