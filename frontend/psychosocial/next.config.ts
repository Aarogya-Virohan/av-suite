import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
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
