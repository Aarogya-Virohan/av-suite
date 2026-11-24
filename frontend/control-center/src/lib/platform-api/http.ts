import axios, { AxiosError, type AxiosInstance } from 'axios';
import type { PlatformApi, TokenProvider } from './api';
import { PLATFORM_ERROR_CODES, PlatformApiError } from './errors';
import { toPlatformApiError } from './http-errors';

/** Public routes: a 401 here is a wrong password or code, not an expired session. */
const PUBLIC_PATHS = ['/auth/login', '/auth/mfa'];

function isPublicPath(url: string | undefined): boolean {
  return !!url && PUBLIC_PATHS.some((path) => url.startsWith(path));
}

/**
 * Real adapter for /api/v1/platform/ (U6). Same PlatformApi as the mock, so
 * screens do not know which one they talk to.
 *
 * `baseUrl` null = the deploy has no NEXT_PUBLIC_API_URL: every call fails
 * with a clear message instead of guessing a host.
 */
export function createHttpPlatformApi(baseUrl: string | null, getToken: TokenProvider, onUnauthorized: () => void): PlatformApi {
  const client: AxiosInstance = axios.create({
    baseURL: baseUrl ? `${baseUrl.replace(/\/+$/, '')}/api/v1/platform` : undefined,
    headers: { 'Content-Type': 'application/json' },
    timeout: 20_000,
  });

  client.interceptors.request.use((config) => {
    if (!baseUrl) {
      return Promise.reject(
        new PlatformApiError(0, { code: 'CONFIG_ERROR', message: 'The Control Center is not connected to the platform API. Tell the AV tech team.' }),
      );
    }
    const token = getToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  client.interceptors.response.use(
    (response) => {
      // A proxy or a wrong URL can answer 200 with HTML. Anything but the envelope is a failure.
      const body = response.data as unknown;
      if (!body || typeof body !== 'object' || !('data' in body)) {
        return Promise.reject(new PlatformApiError(502, { code: 'BAD_RESPONSE', message: 'The server sent an unexpected answer. Try again.' }));
      }
      return response;
    },
    (error: unknown) => {
      if (error instanceof PlatformApiError) return Promise.reject(error);
      const axiosError = error as AxiosError;
      const status = axiosError.response?.status ?? 0;
      if (status === 401 && !isPublicPath(axiosError.config?.url)) onUnauthorized();
      return Promise.reject(toPlatformApiError(status, axiosError.response?.data));
    },
  );

  const get = async <T>(url: string, params?: object) => (await client.get<T>(url, { params: cleanParams(params) })).data;
  const post = async <T>(url: string, body?: unknown) => (await client.post<T>(url, body)).data;
  const patch = async <T>(url: string, body: unknown) => (await client.patch<T>(url, body)).data;
  const put = async <T>(url: string, body: unknown) => (await client.put<T>(url, body)).data;
  const id = encodeURIComponent;

  return {
    login: (body) => post('/auth/login', body),
    verifyMfa: (body) => post('/auth/mfa', body),
    getOverview: () => get('/overview'),
    getUsage: (params) => get('/usage', params),
    listProducts: () => get('/products'),
    listOrganizations: (params) => get('/organizations', params),
    createOrganization: (body) => post('/organizations', body),
    getOrganization: (orgId) => get(`/organizations/${id(orgId)}`),
    updateOrganization: (orgId, body) => patch(`/organizations/${id(orgId)}`, body),
    suspendOrganization: (orgId, body) => post(`/organizations/${id(orgId)}/suspend`, body),
    activateOrganization: (orgId, body) => post(`/organizations/${id(orgId)}/activate`, body),
    createClinic: (orgId, body) => post(`/organizations/${id(orgId)}/clinics`, body),
    mergeOrganization: (orgId, body) => post(`/organizations/${id(orgId)}/merge`, body),
    getClinic: (clinicId) => get(`/clinics/${id(clinicId)}`),
    suspendClinic: (clinicId, body) => post(`/clinics/${id(clinicId)}/suspend`, body),
    activateClinic: (clinicId, body) => post(`/clinics/${id(clinicId)}/activate`, body),
    setClinicProduct: (clinicId, productKey, body) => put(`/clinics/${id(clinicId)}/products/${id(productKey)}`, body),
    listAuditLogs: (params) => get('/audit-logs', params),
    listOperators: (params) => get('/operators', params),
    // No POST /operators route exists (S2 rule: operators are created from the CLI only).
    createOperator: () =>
      Promise.reject(
        new PlatformApiError(403, {
          code: PLATFORM_ERROR_CODES.FORBIDDEN,
          message: 'Operators are created from the command line only.',
        }),
      ),
    updateOperator: (opId, body) => patch(`/operators/${id(opId)}`, body),
  };
}

/** Drop undefined / empty values so they never reach the query string. */
function cleanParams(params: object | undefined): object | undefined {
  if (!params) return undefined;
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''));
}
