import { defineConfig } from 'vitest/config';

// Unit tests live next to the code in src/. The e2e/ folder belongs to
// Playwright (`npm run e2e`) and must not be collected by vitest.
export default defineConfig({
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
