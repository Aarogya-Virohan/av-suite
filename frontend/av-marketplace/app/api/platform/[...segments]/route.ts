import { cookies } from 'next/headers';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import {
  getBackendApiUrl,
  readJson,
  SESSION_COOKIE_NAME,
} from '../../../../lib/server/backend';

type RouteParameters = { params: Promise<{ segments: string[] }> };

function isAllowedRequest(method: string, path: string): boolean {
  if (method === 'GET') {
    return path === 'me'
      || path === 'marketplace/products'
      || path === 'marketplace/installed';
  }
  if (method !== 'POST') return false;

  return /^marketplace\/products\/[a-zA-Z0-9_-]+\/(install|enable|disable)$/.test(path)
    || /^marketplace\/bundles\/[a-zA-Z0-9_-]+\/install$/.test(path);
}

async function proxyRequest(request: NextRequest, context: RouteParameters) {
  const { segments } = await context.params;
  const path = segments.join('/');
  if (!isAllowedRequest(request.method, path)) {
    return Response.json({ detail: 'Platform endpoint not found.' }, { status: 404 });
  }

  const session = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!session) {
    return Response.json({ detail: 'Your session has expired. Sign in again.' }, { status: 401 });
  }

  try {
    const backendResponse = await fetch(
      `${getBackendApiUrl(path)}${request.nextUrl.search}`,
      {
        method: request.method,
        headers: { Authorization: `Bearer ${session}`, Accept: 'application/json' },
        cache: 'no-store',
      },
    );
    const payload: unknown = await readJson(backendResponse);
    if (backendResponse.status >= 500) {
      return Response.json(
        { detail: 'The platform service is unavailable. Try again shortly.' },
        { status: 503, headers: { 'Cache-Control': 'no-store' } },
      );
    }
    if (backendResponse.status === 401) {
      const response = NextResponse.json(
        { detail: 'Your session has expired. Sign in again.' },
        { status: 401, headers: { 'Cache-Control': 'no-store' } },
      );
      response.cookies.delete(SESSION_COOKIE_NAME);
      return response;
    }
    return Response.json(payload, {
      status: backendResponse.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return Response.json(
      { detail: 'The platform service is unavailable. Check the backend configuration.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;