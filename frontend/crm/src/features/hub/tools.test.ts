import { afterEach, describe, expect, it, vi } from 'vitest';

async function load(env: Record<string, string>) {
  vi.resetModules();
  for (const [k, v] of Object.entries(env)) vi.stubEnv(k, v);
  return import('./tools');
}

afterEach(() => vi.unstubAllEnvs());

describe('toolState (HUB-3)', () => {
  it('hub mode: granted tool opens its hub path', async () => {
    const { TOOLS, toolState } = await load({ NEXT_PUBLIC_BASE_PATH: '/crm' });
    const posture = TOOLS.find((t) => t.key === 'posture')!;
    expect(toolState(posture, new Set(['posture-tool']), { 'posture.view': 'all' })).toEqual({ kind: 'open', href: '/posture' });
  });

  it('product not enabled = not in your plan, even with the capability', async () => {
    const { TOOLS, toolState } = await load({ NEXT_PUBLIC_BASE_PATH: '/crm' });
    const posture = TOOLS.find((t) => t.key === 'posture')!;
    expect(toolState(posture, new Set(['crm']), { 'posture.view': 'all' }).kind).toBe('not-in-plan');
  });

  it('product enabled but no capability = no access', async () => {
    const { TOOLS, toolState } = await load({ NEXT_PUBLIC_BASE_PATH: '/crm' });
    const posture = TOOLS.find((t) => t.key === 'posture')!;
    expect(toolState(posture, new Set(['posture-tool']), { 'posture.view': 'none' }).kind).toBe('no-access');
  });

  it('any one of the capabilities is enough; unknown entitlement does not block', async () => {
    const { TOOLS, toolState } = await load({ NEXT_PUBLIC_BASE_PATH: '/crm' });
    const screening = TOOLS.find((t) => t.key === 'screening')!;
    expect(toolState(screening, null, { 'screening.view': 'own' }).kind).toBe('open');
  });

  it('standalone without a tool URL = not available; with URL = that URL', async () => {
    const a = await load({ NEXT_PUBLIC_BASE_PATH: '' });
    const ex = a.TOOLS.find((t) => t.key === 'exercises')!;
    expect(a.toolState(ex, new Set(['exercise-library']), { 'exercises.view': 'all' }).kind).toBe('unavailable');
    const b = await load({ NEXT_PUBLIC_BASE_PATH: '', NEXT_PUBLIC_EXERCISE_APP_URL: 'https://el.example.app/' });
    const ex2 = b.TOOLS.find((t) => t.key === 'exercises')!;
    expect(b.toolState(ex2, new Set(['exercise-library']), { 'exercises.view': 'all' })).toEqual({
      kind: 'open',
      href: 'https://el.example.app',
    });
  });
});
