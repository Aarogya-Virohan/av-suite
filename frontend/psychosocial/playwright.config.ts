import { defineConfig } from '@playwright/test';

/**
 * End-to-end run against a real backend and a production build:
 *   backend on API_URL (default http://localhost:8000) with this app's origin
 *   in CORS_ORIGINS, then `npm run build && npm start`, then `npm run e2e`.
 * Test data is created through the public API (register, marketplace
 * install, users, permissions, patients), so no seed script is needed.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.APP_URL || 'http://localhost:3005',
    trace: 'retain-on-failure',
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
  },
  projects: [
    { name: 'phone', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
  ],
});
