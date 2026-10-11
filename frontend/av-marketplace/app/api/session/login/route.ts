import { NextResponse } from 'next/server';

import {
  backendErrorResponse,
  getBackendApiUrl,
  isRecord,
  readJson,
  SESSION_COOKIE_NAME,
} from '../../../../lib/server/backend';

export async function POST(request: Request) {
  const body: unknown = await request.json().catch(() => null);
  if (
    !isRecord(body)
    || typeof body.email !== 'string'
    || typeof body.password !== 'string'
    || !body.email.trim()
    || !body.password
  ) {
    return Response.json({ detail: 'Enter your email and password.' }, { status: 400 });
  }

  try {
    const backendResponse = await fetch(getBackendApiUrl('auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email: body.email, password: body.password }),
      cache: 'no-store',
    });
    const payload: unknown = await readJson(backendResponse);
    if (!backendResponse.ok) {
      return backendErrorResponse(backendResponse.status, payload);
    }

    const envelopeData = isRecord(payload) ? payload.data : null;
    const token = isRecord(envelopeData) ? envelopeData.access_token : null;
    if (typeof token !== 'string' || !token) {
      return Response.json(
        { detail: 'The platform returned an invalid sign-in response.' },
        { status: 502 },
      );
    }

    const response = NextResponse.json({ data: { authenticated: true } });
    response.cookies.set(SESSION_COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
    });
    return response;
  } catch {
    return Response.json(
      { detail: 'The platform service is unavailable. Check the backend configuration.' },
      { status: 503 },
    );
  }
}