export const SESSION_COOKIE_NAME = 'av_platform_session';

export function getBackendApiUrl(path: string): string {
  const configuredUrl = process.env.BACKEND_API_URL?.trim();
  if (!configuredUrl) {
    throw new Error('BACKEND_API_URL is not configured.');
  }

  const baseUrl = new URL(configuredUrl);
  if (!['http:', 'https:'].includes(baseUrl.protocol) || baseUrl.pathname !== '/') {
    throw new Error('BACKEND_API_URL must be an HTTP(S) origin without a path.');
  }

  return new URL(`/api/v1/${path}`, baseUrl).toString();
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export async function readJson(response: Response): Promise<unknown> {
  return response.json().catch(() => null);
}

export function backendErrorResponse(status: number, payload: unknown): Response {
  if (status >= 500) {
    return Response.json(
      { detail: 'The platform service is unavailable. Try again shortly.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    );
  }

  if (isRecord(payload)) {
    const detail = payload.detail;
    if (typeof detail === 'string') {
      return Response.json({ detail }, { status, headers: { 'Cache-Control': 'no-store' } });
    }
    const meta = payload.meta;
    if (isRecord(meta) && isRecord(meta.error)) {
      return Response.json(
        { detail: meta.error.message ?? 'The request could not be completed.' },
        { status, headers: { 'Cache-Control': 'no-store' } },
      );
    }
  }

  return Response.json(
    { detail: status === 401 ? 'Email or password is incorrect.' : 'The request could not be completed.' },
    { status, headers: { 'Cache-Control': 'no-store' } },
  );
}