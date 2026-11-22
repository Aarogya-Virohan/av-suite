/**
 * L1 hub smoke (HUB-1..HUB-4, HUB-6): one URL, one login, tools launcher.
 * Needs the hub stack (CRM /crm with rewrites, tools built with base paths)
 * and the demo seed. HUB_PSQL (local DB URL) lets the test switch one
 * product off for the "not in your plan" check; never point it at staging/prod.
 */
import { test, expect, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const PASS = process.env.AV_SEED_PASSWORD || '';
const PSQL = process.env.HUB_PSQL || '';
const SHOTS = process.env.SHOTS_DIR || 'shots';
let n = 0;
const shot = (page: Page, name: string) =>
  page.screenshot({ path: `${SHOTS}/${String(++n).padStart(2, '0')}-${name}.png`, fullPage: false });

function sql(q: string) {
  if (!/localhost|127\.0\.0\.1/.test(PSQL)) throw new Error('HUB_PSQL must be a local database');
  execFileSync('psql', [PSQL, '-qc', q]);
}

async function login(page: Page, email: string) {
  await page.getByLabel('Email Address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASS);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

test.describe.configure({ mode: 'serial' });

test('1. bare hub URL opens the common AV Suite login (no sign-up link)', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/crm\/login(\?next=%2Fcrm%2Fdashboard)?$/);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await expect(page.getByText('Sign in to AV Suite')).toBeVisible();
  await expect(page.getByRole('link', { name: /sign up|register/i })).toHaveCount(0);
  await shot(page, 'hub-login');
});

test('2. one login works in all four tools', async ({ page }) => {
  await page.goto('/crm/login');
  await login(page, 'admin@physiodemo.in');
  await expect(page).toHaveURL(/\/crm\/dashboard/);
  const tools = page.getByTestId('hub-tools');
  for (const label of ['Exercise Library', 'Posture Analysis', 'Psychosocial Screening']) {
    await expect(tools.getByRole('link', { name: label })).toBeVisible();
  }
  await shot(page, 'crm-dashboard-tools');

  await tools.getByRole('link', { name: 'Exercise Library' }).click();
  await expect(page).toHaveURL(/\/exercises\/?$/);
  await expect(page.getByText('Exercise Library').first()).toBeVisible();
  await expect(page.getByTestId('back-to-crm')).toBeVisible();
  await page.waitForLoadState('networkidle');
  await shot(page, 'exercises-signed-in');

  await page.getByTestId('back-to-crm').click();
  await expect(page).toHaveURL(/\/crm\/dashboard/);

  await page.goto('/posture');
  await expect(page).toHaveURL(/\/posture\/?$/);
  await expect(page.getByText('Posture Tool')).toBeVisible();
  await expect(page.getByTestId('back-to-crm')).toBeVisible();
  await shot(page, 'posture-signed-in');

  await page.goto('/screening/sessions');
  await expect(page).toHaveURL(/\/screening\/sessions/);
  await expect(page.getByTestId('back-to-crm').first()).toBeVisible();
  await page.waitForLoadState('networkidle');
  await shot(page, 'screening-signed-in');
});

test('3. logout in one tool logs out everywhere; deep link comes back after login', async ({ page }) => {
  await page.goto('/crm/login');
  await login(page, 'admin@physiodemo.in');
  await expect(page).toHaveURL(/\/crm\/dashboard/);
  await page.goto('/exercises');
  await page.getByRole('button', { name: /log ?out|sign out/i }).first().click();
  await expect(page).toHaveURL(/\/crm\/login/);
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();

  await page.goto('/crm/dashboard');
  await expect(page).toHaveURL(/\/crm\/login/);
  await page.goto('/posture/analyze?patient_id=demo');
  await expect(page).toHaveURL(/\/crm\/login\?next=%2Fposture%2Fanalyze%3Fpatient_id%3Ddemo/);
  await shot(page, 'login-with-next');
  await login(page, 'admin@physiodemo.in');
  await expect(page).toHaveURL(/\/posture\/analyze\?patient_id=demo/);
});

test('4. expired / bad token goes to the hub login with a message', async ({ page }) => {
  await page.goto('/crm/login');
  await page.evaluate(() => localStorage.setItem('token', 'not-a-real-token'));
  await page.goto('/exercises');
  await expect(page).toHaveURL(/\/crm\/login\?expired=1/);
  await expect(page.getByText('Your session has ended. Please sign in again.')).toBeVisible();
  await shot(page, 'expired');
});

test('5. not-granted tools stay visible but disabled', async ({ page }) => {
  test.skip(!PSQL, 'HUB_PSQL not set');
  sql(`update workspace_products set status='disabled' where product_id='psycho-social-screening'`);
  try {
    await page.goto('/crm/login');
    await login(page, 'admin@physiodemo.in');
    const tools = page.getByTestId('hub-tools');
    const screening = tools.locator('[data-tool="screening"]');
    await expect(screening).toHaveAttribute('aria-disabled', 'true');
    await expect(screening).toContainText('Not in your plan');
    await expect(tools.getByRole('link', { name: 'Exercise Library' })).toBeVisible();
    await shot(page, 'admin-screening-not-in-plan');
  } finally {
    sql(`update workspace_products set status='enabled' where product_id='psycho-social-screening'`);
  }
  await page.evaluate(() => localStorage.clear());
  await page.goto('/crm/login');
  await login(page, 'frontdesk@physiodemo.in');
  await expect(page).toHaveURL(/\/crm\//);
  const posture = page.getByTestId('hub-tools').locator('[data-tool="posture"]');
  await expect(posture).toHaveAttribute('aria-disabled', 'true');
  await expect(posture).toContainText('Ask your admin for access');
  await shot(page, 'frontdesk-tools');
});

test('6. old CRM links and old tool URLs still land in the hub', async ({ page, request }) => {
  const r = await request.get('/booking/av-demo-physio', { maxRedirects: 0 });
  expect(r.status()).toBe(307);
  expect(r.headers()['location']).toMatch(/\/crm\/booking\/av-demo-physio$/);
  await page.goto('/booking/av-demo-physio');
  await expect(page).toHaveURL(/\/crm\/booking\/av-demo-physio/);
  await shot(page, 'old-booking-link');
  const standalone = process.env.POSTURE_DIRECT || 'http://localhost:3002/';
  const r2 = await request.get(standalone, { maxRedirects: 0 });
  expect(r2.status()).toBe(307);
  expect(r2.headers()['location']).toMatch(/\/posture$/);
});

test('7. phone width: login and tools menu', async ({ browser }) => {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto('/crm/login');
  await shot(page, 'phone-login');
  await login(page, 'therapist@physiodemo.in');
  await expect(page).toHaveURL(/\/crm\//);
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(page.getByTestId('hub-tools').getByRole('link', { name: 'Exercise Library' })).toBeVisible();
  await shot(page, 'phone-tools-menu');
  await page.close();
});
