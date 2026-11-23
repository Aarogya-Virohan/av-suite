import { expect, test } from '@playwright/test';

// Mock mode must keep working for local dev. Run against `next dev` (mode unset = mock):
//   MOCK_SMOKE=1 CC_URL=http://localhost:3007 npx playwright test mock-smoke
test.skip(!process.env.MOCK_SMOKE, 'set MOCK_SMOKE=1 and CC_URL to a mock-mode dev server');

test('mock mode: badge, sign-in with any 6-digit code, pages load, no network call to a backend', async ({ page }) => {
  const calls: string[] = [];
  page.on('request', (r) => {
    if (r.url().includes('/api/v1/')) calls.push(r.url());
  });
  await page.goto('/login');
  await expect(page.getByText('Mock data').first()).toBeVisible();
  await page.locator('#login-email').fill('onkar@av-console.mock');
  await page.locator('#login-password').fill('whatever-123');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.locator('#mfa-code').fill('123456');
  await page.getByRole('button', { name: /Verify and/ }).click();
  await expect(page).toHaveURL(/\/overview$/);
  for (const path of ['/organizations', '/usage', '/audit-logs', '/operators']) {
    await page.goto(path);
    await expect(page.locator('main h1').first()).toBeVisible();
  }
  await page.goto('/usage');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  expect(calls).toEqual([]);
});
