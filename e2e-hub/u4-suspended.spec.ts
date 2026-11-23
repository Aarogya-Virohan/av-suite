/**
 * U4 (HUB-5 / PLT-2 U4): suspended workspace screen in all four apps, and
 * launcher validity (expired entitlement = "Not in your plan").
 * Needs the hub stack + demo seed. HUB_PSQL must be a LOCAL database: the
 * test suspends the demo clinic / organization by SQL and restores it.
 */
import { test, expect, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const PASS = process.env.AV_SEED_PASSWORD || '';
const PSQL = process.env.HUB_PSQL || '';
const SHOTS = process.env.SHOTS_DIR || 'shots';
const TITLE = "Your clinic's access is paused. Please contact AV support.";
const CLINIC = `(select id from clinics where slug='av-demo-physio')`;
const ORG = `(select organization_id from clinics where slug='av-demo-physio')`;

function sql(q: string) {
  if (!/localhost|127\.0\.0\.1/.test(PSQL)) throw new Error('HUB_PSQL must be a local database');
  execFileSync('psql', [PSQL, '-qc', q]);
}
const suspendClinic = () => sql(`update clinics set status='suspended' where id=${CLINIC}`);
const suspendOrg = () => sql(`update organizations set status='suspended' where id=${ORG}`);
const restore = () => {
  sql(`update clinics set status='active' where id=${CLINIC}`);
  sql(`update organizations set status='active' where id=${ORG}`);
};

async function login(page: Page) {
  await page.goto('/crm/login');
  await page.getByLabel('Email Address').fill('admin@physiodemo.in');
  await page.getByLabel('Password', { exact: true }).fill(PASS);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

async function expectScreen(page: Page, detail: string, name: string, w: number) {
  const screen = page.getByTestId('suspended-screen');
  await expect(screen).toBeVisible();
  await expect(screen.getByRole('heading', { name: TITLE })).toBeVisible();
  await expect(screen.getByText(detail, { exact: true })).toBeVisible();
  await expect(screen.getByRole('button')).toHaveCount(1);
  await expect(screen.getByRole('button', { name: 'Back to sign in' })).toBeVisible();
  await expect(screen).not.toContainText(/@|\+91|phone|email/i);
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();
  await page.screenshot({ path: `${SHOTS}/u4-${w}-${name}.png` });
}

test.describe.configure({ mode: 'serial' });
test.beforeAll(() => {
  if (!PSQL) throw new Error('HUB_PSQL not set');
});
test.afterEach(() => restore());

for (const [w, h] of [[1440, 900], [390, 844]] as const) {
  test.describe(`${w}px`, () => {
    test.use({ viewport: { width: w, height: h } });

    test(`login with clinic suspended shows the screen (${w})`, async ({ page }) => {
      suspendClinic();
      await login(page);
      await expectScreen(page, 'This clinic is paused.', 'crm-login-clinic', w);
      await page.getByRole('button', { name: 'Back to sign in' }).click();
      await expect(page).toHaveURL(/\/crm\/login/);
      await expect(page.getByTestId('suspended-screen')).toHaveCount(0);
    });

    for (const [tool, path] of [
      ['crm', '/crm/dashboard'],
      ['posture', '/posture'],
      ['exercises', '/exercises'],
      ['screening', '/screening/sessions'],
    ] as const) {
      test(`signed in, then clinic suspended: ${tool} shows the screen on the next call (${w})`, async ({ page }) => {
        await login(page);
        await expect(page).toHaveURL(/\/crm\/dashboard/);
        await page.goto(path);
        await page.waitForLoadState('networkidle');
        await expect(page.getByTestId('suspended-screen')).toHaveCount(0);
        suspendClinic();
        await page.reload();
        await expectScreen(page, 'This clinic is paused.', `${tool}-clinic`, w);
        await page.getByRole('button', { name: 'Back to sign in' }).click();
        await expect(page).toHaveURL(/\/crm\/login/);
      });
    }
  });
}

test('organization suspended: organization line (once)', async ({ page }) => {
  suspendOrg();
  await login(page);
  await expectScreen(page, "Your organization's account is paused.", 'crm-login-org', 1440);
});

test('restore: login works normally again', async ({ page }) => {
  restore();
  await login(page);
  await expect(page).toHaveURL(/\/crm\/dashboard/);
  await expect(page.getByTestId('suspended-screen')).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}/u4-1440-restored.png` });
});

test('expired entitlement: sidebar tool is "Not in your plan"', async ({ page }) => {
  sql(`update workspace_products set valid_until=now() - interval '1 day' where product_id='posture-tool' and clinic_id=${CLINIC}`);
  try {
    await login(page);
    await expect(page).toHaveURL(/\/crm\/dashboard/);
    const posture = page.getByTestId('hub-tools').locator('[data-tool="posture"]');
    await expect(posture).toHaveAttribute('aria-disabled', 'true');
    await expect(posture).toContainText('Not in your plan');
    await expect(page.getByTestId('hub-tools').getByRole('link', { name: 'Exercise Library' })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/u4-1440-expired-not-in-plan.png` });
  } finally {
    sql(`update workspace_products set valid_until=null where product_id='posture-tool' and clinic_id=${CLINIC}`);
  }
});
