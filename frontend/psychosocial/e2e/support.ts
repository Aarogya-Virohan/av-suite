import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const API = (process.env.API_URL || 'http://localhost:8000').replace(/\/$/, '') + '/api/v1';
export const SHOTS = 'e2e/.artifacts';

export interface Clinic {
  adminEmail: string;
  adminToken: string;
  therapistEmail: string;
  therapistToken: string;
  password: string;
  patientId: string;
  patientFirst: string;
  patientLast: string;
}

async function ok<T>(res: Awaited<ReturnType<APIRequestContext['post']>>): Promise<T> {
  const body = await res.json().catch(() => null);
  expect(res.ok(), `${res.url()} -> ${res.status()} ${JSON.stringify(body)}`).toBeTruthy();
  return (body as { data: T }).data;
}

async function login(request: APIRequestContext, email: string, password: string): Promise<string> {
  const data = await ok<{ access_token: string }>(await request.post(`${API}/auth/login`, { data: { email, password } }));
  return data.access_token;
}

/** A fresh clinic with the screening product, one therapist and one patient. */
export async function makeClinic(request: APIRequestContext): Promise<Clinic> {
  const tag = Math.random().toString(36).slice(2, 8);
  const password = 'Password123!';
  const adminEmail = `admin_${tag}@e2e-avsuite.in`;
  const reg = await ok<{ access_token: string }>(
    await request.post(`${API}/auth/register`, {
      data: { clinic_name: `Sunrise Physio ${tag}`, email: adminEmail, password, first_name: 'Neha', last_name: 'Kapoor' },
    }),
  );
  const admin = { Authorization: `Bearer ${reg.access_token}` };
  await ok(await request.post(`${API}/marketplace/products/psycho-social-screening/install`, { headers: admin }));

  const therapistEmail = `physio_${tag}@e2e-avsuite.in`;
  const therapist = await ok<{ id: string }>(
    await request.post(`${API}/users`, {
      headers: admin,
      data: { name: 'Arjun Mehta', first_name: 'Arjun', last_name: 'Mehta', email: therapistEmail, password, role: 'therapist' },
    }),
  );
  await ok(
    await request.put(`${API}/users/${therapist.id}/permissions`, {
      headers: admin,
      data: [
        { capability_key: 'patients.view', scope: 'all' },
        { capability_key: 'patients.create', scope: 'all' },
        { capability_key: 'screening.assign', scope: 'all' },
        { capability_key: 'screening.view', scope: 'own' },
        { capability_key: 'screening.refer', scope: 'own' },
      ],
    }),
  );
  const patient = await ok<{ id: string }>(
    await request.post(`${API}/patients`, {
      headers: admin,
      data: { first_name: 'Ritu', last_name: `Sharma${tag}`, phone: '9876543210' },
    }),
  );
  return {
    adminEmail,
    adminToken: reg.access_token,
    therapistEmail,
    therapistToken: await login(request, therapistEmail, password),
    password,
    patientId: patient.id,
    patientFirst: 'Ritu',
    patientLast: `Sharma${tag}`,
  };
}

export async function assignVia(
  request: APIRequestContext,
  token: string,
  patientId: string,
  instruments: string[],
): Promise<string> {
  const data = await ok<{ screener_path: string }>(
    await request.post(`${API}/patients/${patientId}/psychosocial/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { instruments, expires_in_days: 7 },
    }),
  );
  return data.screener_path;
}

export async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/sessions');
}

/**
 * Collects console errors and failed or 5xx network calls. `allow` lists
 * expected HTTP statuses (an error page test expects its 404 or 410).
 */
export function watch(page: Page, allow: number[] = []) {
  const problems: string[] = [];
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const text = m.text();
    if (allow.some((s) => text.includes(`status of ${s}`))) return;
    problems.push(`console: ${text}`);
  });
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('requestfailed', (r) => {
    const failure = r.failure()?.errorText ?? '';
    if (failure.includes('ERR_ABORTED')) return; // navigation cancelling an in-flight request
    problems.push(`requestfailed: ${r.url()} ${failure}`);
  });
  page.on('response', (r) => {
    if (r.status() >= 400 && !allow.includes(r.status())) problems.push(`http ${r.status()}: ${r.url()}`);
  });
  return problems;
}

export async function shot(page: Page, name: string) {
  const project = page.viewportSize()!.width < 600 ? 'phone' : 'desktop';
  await page.waitForTimeout(350); // let the 220 ms entry animation finish
  await page.screenshot({ path: `${SHOTS}/${project}-${name}.png`, fullPage: true });
}
