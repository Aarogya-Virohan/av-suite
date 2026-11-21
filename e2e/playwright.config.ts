import { defineConfig, devices } from "@playwright/test";

// AV Suite smoke suite (launch-plan EN-3). Targets come from env so the same
// suite runs on the container stack (scripts/local-stack.sh) and on staging.
// Never point it at production: it creates leads, patients, invoices and Rx.
export default defineConfig({
  testDir: "./tests",
  outputDir: "out/test-results",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "out/results.json" }]],
  use: {
    timezoneId: "Asia/Kolkata",
    locale: "en-IN",
    actionTimeout: 20_000,
    navigationTimeout: 45_000,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-1440", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    {
      name: "mobile-390",
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
  ],
});
