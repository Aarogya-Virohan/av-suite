import type { NextConfig } from "next";

const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline' https://challenges.cloudflare.com;
  frame-src 'self' https://challenges.cloudflare.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data:;
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 https://challenges.cloudflare.com ws://localhost:3000 wss://localhost:3000 https://* wss://*;
`.replace(/\n/g, '');

// HUB-1: one URL for every tool. Off unless NEXT_PUBLIC_BASE_PATH is set
// (e.g. "/crm"), so today's prod build is unchanged until the cutover.
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '');

// Origins of the other tool deployments (each built with its own base path).
// Server-side only; read at build time on Vercel.
const TOOL_ORIGINS: Array<[string, string | undefined]> = [
  ['/posture', process.env.HUB_POSTURE_ORIGIN],
  ['/exercises', process.env.HUB_EXERCISES_ORIGIN],
  ['/screening', process.env.HUB_SCREENING_ORIGIN],
];

function origin(value: string): string {
  return value.replace(/\/+$/, '');
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(basePath ? { basePath } : {}),
  async redirects() {
    if (!basePath) return [];
    return [
      // The bare hub URL opens the CRM.
      { source: '/', destination: basePath, basePath: false, permanent: false },
      // Old CRM links without the base path (bookmarks, shared booking
      // links /booking/<slug>) keep working after the cutover.
      {
        source: '/:path((?!crm(?:/|$)|posture(?:/|$)|exercises(?:/|$)|screening(?:/|$)|_next/|favicon).*)',
        destination: `${basePath}/:path`,
        basePath: false,
        permanent: false,
      },
    ];
  },
  async rewrites() {
    if (!basePath) return [];
    return TOOL_ORIGINS.filter(([, o]) => !!o).flatMap(([path, o]) => [
      { source: path, destination: `${origin(o as string)}${path}`, basePath: false as const },
      { source: `${path}/:path*`, destination: `${origin(o as string)}${path}/:path*`, basePath: false as const },
    ]);
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspHeader,
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains; preload',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
