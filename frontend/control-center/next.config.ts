import type { NextConfig } from 'next';

const isProduction = process.env.NODE_ENV === 'production';
// A production build never falls back to a local backend: no URL, no extra origin.
const apiOrigin = (process.env.NEXT_PUBLIC_API_URL || (isProduction ? '' : 'http://localhost:8000')).replace(/\/+$/, '');
const devSocket = isProduction ? '' : 'ws://localhost:3006 wss://localhost:3006';

const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data:;
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  connect-src 'self' ${apiOrigin} ${devSocket};
`.replace(/\n/g, '');

// Same rule as resolveApiMode() in src/lib/platform-api/index.ts. Setting it here
// means the value always exists at build time, so a production build without it
// compiles the mock adapter out of the bundle (scripts/check-bundle.mjs proves it).
const requestedMode = process.env.NEXT_PUBLIC_PLATFORM_API_MODE;
const platformApiMode = requestedMode === 'mock' || requestedMode === 'http' ? requestedMode : isProduction ? 'http' : 'mock';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: { NEXT_PUBLIC_PLATFORM_API_MODE: platformApiMode },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: cspHeader },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains; preload' },
          { key: 'Referrer-Policy', value: 'no-referrer' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          { key: 'X-Robots-Tag', value: 'noindex, nofollow' },
        ],
      },
    ];
  },
};

export default nextConfig;
