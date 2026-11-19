import axios, { AxiosError, type AxiosInstance } from 'axios';
import type { PlatformApi, TokenProvider } from './api';
import { PLATFORM_ERROR_CODES, PlatformApiError } from './errors';
import type { MetaError } from './types';

/**
 * Real adapter for /api/v1/platform/. Used once S2/S3 are live (U5/U6);
 * only the base URL and this file are involved in the switch, never screens.
 */
export function createHttpPlatformApi(baseUrl: string, getToken: TokenProvider, onUnauthorized: () => void): PlatformApi {
  const client: AxiosInstance = axios.create({
    baseURL: `${baseUrl.replace(/\/+$/, '')}/api/v1/platform`,
    headers: { 'Content-Type': 'application/json' },
    timeout: 20_000,
  });

  client.interceptors.request.use((config) => {
    const token = getToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError<Partial<MetaError> | { meta?: MetaError | null; detail?: unknown }>) => {
      const status = error.response?.status ?? 0;
      if (status === 401) onUnauthorized();
      const body = error.response?.data as { meta?: Partial<MetaError> | null; detail?: unknown } | undefined;
      const envelopeError = body?.meta?.error;
      if (envelopeError?.code) return Promise.reject(new PlatformApiError(status, envelopeError));
      const detail = typeof body?.detail === 'string' ? body.detail : undefined;
      return Promise.reject(
        new PlatformApiError(status, {
          code: status === 0 ? PLATFORM_ERROR_CODES.NETWORK_ERROR : `HTTP_${status}`,
          message: detail ?? (status === 0 ? 'Cannot reach the server.' : 'Request failed.'),
        }),
      );
    },
  );

  const get = async <T>(url: string, params?: object) => (await client.get<T>(url, { params })).data;
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
    createOperator: (body) => post('/operators', body),
    updateOperator: (opId, body) => patch(`/operators/${id(opId)}`, body),
  };
}
