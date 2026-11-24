import { execSync } from 'node:child_process';
import { createHmac } from 'node:crypto';
import { mkdirSync, readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';

/*
 * L8: Control Center on real data. One serial run per project against a fresh
 * local stack (e2e/local-stack.sh): operators come from the CLI and are not
 * enrolled yet. LOCAL ONLY.
 */

const STACK_DIR = process.env.STACK_DIR || '/tmp/l8-stack';
const API = process.env.API_URL || 'http://localhost:8000';
// psql against the LOCAL database only (the stack script's database).
const PSQL = process.env.L8_PSQL || 'su av -c "psql -h /var/tmp -p 5433 -d l8_console -At -q -v ON_ERROR_STOP=1 -f -"';

function env(name: string): string {
  const line = readFileSync(`${STACK_DIR}/stack.env`, 'utf8').split('\n').find((l) => l.startsWith(`${name}=`));
  if (!line) throw new Error(`${name} missing in stack.env`);
  return line.slice(name.length + 1).trim();
}

function sql(query: string): string {
  return execSync(PSQL, { input: query, encoding: 'utf8' }).trim();
}

/* ---------- TOTP (RFC 6238, SHA-1, 6 digits, 30 s) ---------- */
function base32(input: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const ch of input.replace(/=+$/, '').toUpperCase()) bits += alphabet.indexOf(ch).toString(2).padStart(5, '0');
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}
function hotp(secret: string, step: number): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(step));
  const digest = createHmac('sha1', base32(secret)).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const value = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return String(value).padStart(6, '0');
}
const lastStep = new Map<string, number>();
/** The backend accepts steps tick-1..tick+1 and never the same step twice. */
async function freshCode(secret: string): Promise<string> {
  for (;;) {
    const tick = Math.floor(Date.now() / 30_000);
    const step = Math.max((lastStep.get(secret) ?? -1) + 1, tick - 1);
    if (step <= tick + 1) {
      lastStep.set(secret, step);
      return hotp(secret, step);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
}

const OWNER_A = { email: 'owner.a@avlocal.in', password: env('OWNER_A_PASSWORD') };
const OWNER_B = { email: 'owner.b@avlocal.in', password: env('OWNER_B_PASSWORD') };
const SUPPORT = { email: 'support@avlocal.in', password: env('SUPPORT_PASSWORD') };
const secrets: Record<string, string> = {};

let n = 0;
async function shot(page: Page, name: string) {
  n += 1;
  const project = test.info().project.name;
  mkdirSync(`shots/${project}`, { recursive: true });
  await page.screenshot({ path: `shots/${project}/${String(n).padStart(2, '0')}-${name}.png`, fullPage: true });
}

async function fillLogin(page: Page, who: { email: string; password: string }) {
  await page.goto('/login');
  await page.locator('#login-email').fill(who.email);
  await page.locator('#login-password').fill(who.password);
  await page.getByRole('button', { name: 'Continue' }).click();
}

async function sessionToken(page: Page): Promise<string> {
  const raw = await page.evaluate(() => window.sessionStorage.getItem('av-control-center.session'));
  return JSON.parse(raw ?? '{}').token as string;
}

/** Direct backend call as the signed-in operator, to hit guards the UI hides. */
async function apiPatchOperator(page: Page, id: string, body: object) {
  const token = await sessionToken(page);
  const res = await page.request.patch(`${API}/api/v1/platform/operators/${id}`, { headers: { Authorization: `Bearer ${token}` }, data: body });
  return { status: res.status(), body: await res.json() };
}

/** Fill the reason in the open slide-over and confirm; waits until it has closed. */
async function confirmWithReason(page: Page, button: string, reason: string) {
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Reason (required)').fill(reason);
  await dialog.getByRole('button', { name: button, exact: true }).click();
  await expect(dialog).toBeHidden();
}

async function signOut(page: Page) {
  // On a phone the menu starts closed: open it first, like a person would.
  if ((page.viewportSize()?.width ?? 1440) < 768) await page.getByRole('button', { name: 'Open menu' }).click();
  await page.getByRole('button', { name: 'Sign out' }).first().click();
  await expect(page).toHaveURL(/\/login$/);
}

async function loginWithCode(page: Page, who: { email: string; password: string }, secret: string) {
  await fillLogin(page, who);
  await expect(page.getByRole('heading', { name: 'Two-step sign-in' })).toBeVisible();
  await page.locator('#mfa-code').fill(await freshCode(secret));
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page).toHaveURL(/\/overview$/);
}

test.describe.configure({ mode: 'serial' });

let page: Page;
let clinicId = '';
let orgId = '';

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  n = 0;
  // Staff activity for the usage page: a real clinic login (platform / login) plus a few rows
  // in the LOCAL database for other tools and days.
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email: 'admin@physiodemo.in', password: env('AV_SEED_PASSWORD') }),
  });
  expect(res.status).toBe(200);
  clinicId = sql("select id from clinics where slug='av-demo-physio'");
  orgId = sql("select organization_id from clinics where slug='av-demo-physio'");
  sql(
    `insert into usage_events (id, organization_id, clinic_id, product_key, event_type, created_at) ` +
      `select gen_random_uuid(), '${orgId}','${clinicId}', p, e, now() - (d || ' days')::interval from (values ` +
      `('crm','patient_created',1),('crm','patient_created',1),('crm','appointment_created',2),('posture-tool','posture_report',2),('exercise-library','prescription_pdf',3)) as t(p,e,d)`,
  );
});
test.afterAll(async () => {
  await page.close();
});

test('login: wrong password shows the real message, nothing is stored', async () => {
  await fillLogin(page, { email: OWNER_A.email, password: 'definitely-wrong' });
  await expect(page.locator('p[role="alert"]')).toHaveText('Email or password is incorrect.');
  expect(await sessionToken(page)).toBeUndefined();
  await shot(page, 'login-wrong-password');
});

test('first login: QR + setup key, wrong code refused, right code signs in (MFA enrolment)', async () => {
  await fillLogin(page, OWNER_A);
  await expect(page.getByRole('heading', { name: 'Set up two-step sign-in' })).toBeVisible();
  await expect(page.getByAltText('QR code for your authenticator app')).toBeVisible();
  const key = (await page.getByTestId('mfa-setup-key').innerText()).replace(/\s+/g, '');
  expect(key).toMatch(/^[A-Z2-7]{32}$/);
  secrets[OWNER_A.email] = key;
  await shot(page, 'mfa-enrolment-qr');

  await page.locator('#mfa-code').fill('000000');
  await page.getByRole('button', { name: 'Verify and finish setup' }).click();
  await expect(page.locator('p[role="alert"]')).toHaveText('The code is not valid.');
  await shot(page, 'mfa-enrolment-wrong-code');

  await page.locator('#mfa-code').fill(await freshCode(key));
  await page.getByRole('button', { name: 'Verify and finish setup' }).click();
  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await expect(page.getByText('Mock data')).toHaveCount(0);
  expect(await sessionToken(page)).toBeTruthy();
  expect(sql(`select mfa_enabled from platform_operators where email='${OWNER_A.email}'`)).toBe('t');
  await shot(page, 'overview-after-enrolment');
});

test('session survives a reload; sign out clears it; MFA login (no QR) works', async () => {
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await signOut(page);
  expect(await sessionToken(page)).toBeUndefined();
  await fillLogin(page, OWNER_A);
  await expect(page.getByRole('heading', { name: 'Two-step sign-in' })).toBeVisible();
  await expect(page.getByAltText('QR code for your authenticator app')).toHaveCount(0);
  await shot(page, 'mfa-login-step');
  await page.locator('#mfa-code').fill(await freshCode(secrets[OWNER_A.email]));
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page).toHaveURL(/\/overview$/);
});

test('organizations: real list, branch add with duplicate slug (409) then a free slug', async () => {
  await page.goto('/organizations');
  await expect(page.getByText('AV Demo Physio').first()).toBeVisible();
  await shot(page, 'organizations-list');
  await page.goto(`/organizations/${orgId}`);
  await expect(page.getByRole('heading', { name: /AV Demo Physio/ })).toBeVisible();
  await page.getByRole('button', { name: 'Add branch' }).click();
  await page.locator('#branch-name').fill('AV Demo Physio Sector 62');
  await page.locator('#branch-slug').fill('av-demo-physio');
  await page.locator('#branch-reason').fill('Second branch for L8 test');
  await page.getByRole('button', { name: 'Add branch' }).last().click();
  await expect(page.getByText('This slug is already used.')).toBeVisible();
  await shot(page, 'branch-duplicate-slug-409');
  await page.locator('#branch-slug').fill('av-demo-physio-s62');
  await page.getByRole('button', { name: 'Add branch' }).last().click();
  await expect(page.getByText('AV Demo Physio Sector 62').first()).toBeVisible();
  await shot(page, 'organization-with-two-branches');
  expect(sql("select count(*) from clinics where slug='av-demo-physio-s62'")).toBe('1');
});

test('clinic suspend -> activate: backend state, staff blocked then allowed', async () => {
  await page.goto(`/clinics/${clinicId}`);
  await expect(page.getByRole('heading', { name: /AV Demo Physio/ }).first()).toBeVisible();
  await shot(page, 'clinic-detail');
  await page.getByRole('button', { name: 'Suspend' }).click();
  await confirmWithReason(page, 'Suspend clinic', 'Payment overdue (L8 test)');
  await expect(page.getByText('Suspended').first()).toBeVisible();
  expect(sql(`select status from clinics where id='${clinicId}'`)).toBe('suspended');
  const blocked = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email: 'admin@physiodemo.in', password: env('AV_SEED_PASSWORD') }),
  });
  expect(blocked.status).toBe(403);
  await shot(page, 'clinic-suspended');

  await page.getByRole('button', { name: 'Activate' }).click();
  await confirmWithReason(page, 'Activate', 'Payment received (L8 test)');
  await expect(page.getByRole('button', { name: 'Suspend' })).toBeVisible();
  expect(sql(`select status from clinics where id='${clinicId}'`)).toBe('active');
  const allowed = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email: 'admin@physiodemo.in', password: env('AV_SEED_PASSWORD') }),
  });
  expect(allowed.status).toBe(200);
  await shot(page, 'clinic-active-again');
});

test('entitlement change: reason required, validity dates, stored and audited', async () => {
  await page.goto(`/clinics/${clinicId}`);
  await expect(page.getByRole('button', { name: /Edit|Grant/ }).first()).toBeVisible();
  await page.getByRole('button', { name: /Edit|Grant/ }).first().click();
  await page.getByLabel('Disabled').check();
  await page.getByRole('button', { name: 'Save access' }).click();
  await expect(page.getByText(/reason/i).first()).toBeVisible();
  await shot(page, 'entitlement-reason-required');
  await page.locator('#valid-from').fill('01/12/2026');
  await page.locator('#valid-until').fill('31/12/2026');
  await page.locator('#entitlement-reason').fill('Plan paused until January (L8 test)');
  await page.getByRole('button', { name: 'Save access' }).click();
  await expect(page.getByRole('button', { name: 'Save access' })).toBeHidden();
  await expect(page.locator('tbody').getByText('Disabled').first()).toBeVisible();
  const row = sql(
    `select product_id||'|'||status||'|'||valid_from::date||'|'||valid_until::date from workspace_products where clinic_id='${clinicId}' and status='disabled' order by updated_at desc limit 1`,
  );
  expect(row).toMatch(/\|disabled\|2026-11-30\|2026-12-31/);
  expect(sql("select count(*) from platform_audit_logs where action='entitlement.updated'")).toBe('1');
  await shot(page, 'entitlement-saved');
});

test('usage page on the real /usage: rows, tool filter, clinic link', async () => {
  await page.goto('/usage');
  await expect(page.getByRole('heading', { name: 'Usage' })).toBeVisible();
  await expect(page.getByText('Patient added').first()).toBeVisible();
  await expect(page.getByText('Staff sign-in').first()).toBeVisible();
  await shot(page, 'usage-all');
  await page.locator('#usage-product').selectOption('crm');
  await expect(page.getByText('Posture report')).toHaveCount(0);
  await expect(page.getByText('Patient added').first()).toBeVisible();
  await shot(page, 'usage-filtered-crm');
  await page.goto(`/usage?clinic_id=${clinicId}`);
  await expect(page.getByText('Showing one clinic only.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'AV Demo Physio' }).first()).toBeVisible();
});

test('audit log: every change above is there with operator and target name', async () => {
  await page.goto('/audit-logs');
  const rows = page.locator('tbody');
  await expect(rows.getByText('Clinic suspended').first()).toBeVisible();
  await expect(rows.getByText('Tool access changed').first()).toBeVisible();
  await expect(rows.getByText('Owner A').first()).toBeVisible();
  await expect(rows.getByText('AV Demo Physio').first()).toBeVisible();
  await shot(page, 'audit-log');
  await page.locator('#audit-action').selectOption('clinic.suspended');
  await expect(rows.getByText('Payment overdue (L8 test)')).toBeVisible();
  await shot(page, 'audit-log-filtered');
  await page.goto('/overview');
  await expect(page.locator('li').getByText('Clinic activated').first()).toBeVisible();
  await shot(page, 'overview-recent-activity');
});

test('operator guards: self 422, role 403, then Owner B deactivated in the UI, last Owner 409', async () => {
  await page.goto('/operators');
  await expect(page.getByText('Owner B').first()).toBeVisible();
  await shot(page, 'operators-list');
  const ops = await (await page.request.get(`${API}/api/v1/platform/operators?page_size=100`, { headers: { Authorization: `Bearer ${await sessionToken(page)}` } })).json();
  const find = (email: string) => ops.data.find((o: { email: string }) => o.email === email).id as string;
  const a = find(OWNER_A.email);
  const b = find(OWNER_B.email);
  const s = find(SUPPORT.email);

  // two active Owners: self-deactivation is 422, a role change is 403 (CLI only)
  let r = await apiPatchOperator(page, a, { is_active: false, reason: 'test' });
  expect(r.status).toBe(422);
  r = await apiPatchOperator(page, s, { role: 'owner', reason: 'test' });
  expect(r.status).toBe(403);

  // UI: deactivate Owner B (allowed), reason required
  await page.getByRole('button', { name: 'Deactivate Owner B' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Deactivate', exact: true }).click();
  await expect(page.getByText('A reason is required.')).toBeVisible();
  await shot(page, 'operators-reason-required');
  await confirmWithReason(page, 'Deactivate', 'Lost laptop (L8 test)');
  await expect(page.getByText('Owner reactivation via CLI').first()).toBeVisible();
  await shot(page, 'operators-owner-b-deactivated');

  // now A is the only active Owner: self + last Owner both apply -> 409 first
  r = await apiPatchOperator(page, a, { is_active: false, reason: 'test' });
  expect(r.status).toBe(409);
  expect(r.body.meta.error.message).toBe('Cannot deactivate the last active Owner');
  // Owner reactivation is CLI only
  r = await apiPatchOperator(page, b, { is_active: true, reason: 'test' });
  expect(r.status).toBe(403);
  // the UI shows the same guard on its own button
  await expect(page.getByRole('button', { name: /Deactivate Owner A: Last active Owner/ })).toBeDisabled();

  // Support: deactivate and reactivate in the UI
  await page.getByRole('button', { name: 'Deactivate Support One' }).click();
  await confirmWithReason(page, 'Deactivate', 'Pause (L8 test)');
  await expect(page.getByRole('button', { name: 'Reactivate Support One' })).toBeVisible();
  await page.getByRole('button', { name: 'Reactivate Support One' }).click();
  await confirmWithReason(page, 'Reactivate', 'Back (L8 test)');
  await expect(page.getByRole('button', { name: 'Deactivate Support One' })).toBeVisible();
  expect(sql("select count(*) from platform_audit_logs where action in ('operator.deactivated','operator.reactivated')")).toBe('3');
  await shot(page, 'operators-final');
});

test('401 sends the operator back to login; a deactivated operator cannot sign in', async () => {
  await page.evaluate(() => {
    const key = 'av-control-center.session';
    const s = JSON.parse(window.sessionStorage.getItem(key) as string);
    s.token = 'not-a-valid-token';
    window.sessionStorage.setItem(key, JSON.stringify(s));
  });
  await page.goto('/organizations');
  await expect(page).toHaveURL(/\/login$/);
  await shot(page, 'expired-token-back-to-login');

  await fillLogin(page, OWNER_B);
  await expect(page.locator('p[role="alert"]')).toHaveText('Email or password is incorrect.');
  await shot(page, 'deactivated-owner-refused');
});

test('Support: reads, but no console writes and no Operators page', async () => {
  await fillLogin(page, SUPPORT);
  await expect(page.getByRole('heading', { name: 'Set up two-step sign-in' })).toBeVisible();
  const key = (await page.getByTestId('mfa-setup-key').innerText()).replace(/\s+/g, '');
  await page.locator('#mfa-code').fill(await freshCode(key));
  await page.getByRole('button', { name: 'Verify and finish setup' }).click();
  await expect(page).toHaveURL(/\/overview$/);
  await page.goto('/operators');
  await expect(page.getByText('Access Restricted')).toBeVisible();
  await shot(page, 'support-operators-restricted');
  await page.goto(`/clinics/${clinicId}`);
  await expect(page.getByRole('heading', { name: /AV Demo Physio/ }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Suspend' })).toHaveCount(0);
  await shot(page, 'support-clinic-read-only');
});
