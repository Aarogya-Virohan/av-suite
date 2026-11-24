import { defineConfig, devices } from '@playwright/test';

// Control Center against a LOCAL backend + local Postgres (e2e/local-stack.sh).
// Never point it at production or staging: it suspends clinics and deactivates operators.
// Run one project per fresh stack (operators start un-enrolled):
//   local-stack.sh up && npx playwright test --project=desktop-1440
//   local-stack.sh up && npx playwright test --project=mobile-390
export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.ts/,
  outputDir: 'out/test-results',
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'out/results.json' }]],
  use: {
    baseURL: process.env.CC_URL || 'http://localhost:3006',
    timezoneId: 'Asia/Kolkata',
    locale: 'en-IN',
    launchOptions: { executablePath: process.env.CHROME || '/usr/bin/google-chrome' },
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop-1440', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile-390', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
