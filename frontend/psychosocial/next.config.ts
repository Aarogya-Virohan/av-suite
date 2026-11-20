import type { NextConfig } from 'next';

// HUB-1: built with NEXT_PUBLIC_BASE_PATH ("/screening") the app is served
// under the hub URL through the CRM project's rewrites. Unset = own URL.
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '');
const hubOrigin = (process.env.NEXT_PUBLIC_HUB_ORIGIN || '').replace(/\/+$/, '');

const nextConfig: NextConfig = {
  ...(basePath ? { basePath } : {}),
  async redirects() {
    if (!basePath || !hubOrigin) return [];
    return [{ source: '/', destination: `${hubOrigin}${basePath}`, basePath: false, permanent: false }];
  },
  // The public screener page must never be indexed or cached by a proxy:
  // the URL itself is the access token.
  async headers() {
    return [
      {
        source: '/screener/:token*',
        headers: [
          { key: 'X-Robots-Tag', value: 'noindex, nofollow' },
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'Referrer-Policy', value: 'no-referrer' },
        ],
      },
    ];
  },
};

export default nextConfig;
