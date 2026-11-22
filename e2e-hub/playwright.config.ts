import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: 'results.json' }]],
  use: {
    baseURL: process.env.HUB_URL || 'http://localhost:3000',
    launchOptions: { executablePath: process.env.CHROME || '/usr/bin/google-chrome' },
    timezoneId: 'Asia/Kolkata',
    viewport: { width: 1440, height: 900 },
  },
});
