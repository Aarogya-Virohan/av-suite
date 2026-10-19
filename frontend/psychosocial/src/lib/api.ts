import { clearStoredToken, getStoredToken } from './auth';

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(status: number, message: string, code: string | null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface Envelope<T> {
  data: T;
  meta?: { total?: number; page?: number; page_size?: number } | null;
}

/**
 * The backend answers errors in three shapes: {detail: string},
 * {detail: {code, message}} and {meta: {error: {code, message}}}.
 * Validation errors come as {detail: [{msg}]}.
 */
function readError(status: number, body: unknown): ApiError {
  const b = (body ?? {}) as {
    detail?: unknown;
    meta?: { error?: { code?: string; message?: string } } | null;
  };
  if (typeof b.detail === 'string') return new ApiError(status, b.detail, null);
  if (Array.isArray(b.detail)) {
    const msg = b.detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join('; ');
    return new ApiError(status, msg || 'Please check the form and try again.', 'VALIDATION');
  }
  if (b.detail && typeof b.detail === 'object') {
    const d = b.detail as { code?: string; message?: string };
    return new ApiError(status, d.message || 'Something went wrong.', d.code ?? null);
  }
  if (b.meta?.error) {
    return new ApiError(status, b.meta.error.message || 'Something went wrong.', b.meta.error.code ?? null);
  }
  return new ApiError(status, `Request failed (${status}).`, null);
}

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<Envelope<T>> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  if (init.auth !== false) {
    const token = getStoredToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      method: init.method ?? 'GET',
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.', 'NETWORK');
  }

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!res.ok) {
    const err = readError(res.status, body);
    if (res.status === 401 && init.auth !== false) {
      clearStoredToken();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login');
      }
    }
    throw err;
  }
  return body as Envelope<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>(path).then((r) => r.data),
  getPage: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body ?? {} }).then((r) => r.data),
  put: <T,>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body }).then((r) => r.data),
};

export const publicApi = {
  get: <T,>(path: string) => request<T>(path, { auth: false }).then((r) => r.data),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ?? {}, auth: false }).then((r) => r.data),
};
