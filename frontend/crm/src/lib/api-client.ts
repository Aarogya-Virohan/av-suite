import axios, { AxiosError } from 'axios';
import { getStoredToken, clearStoredTokens } from './auth';
import { useAuthStore } from '../store';

const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BASE_URL = rawBaseUrl.replace(/\/+$/, '');
export const API_BASE_URL = `${BASE_URL}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Backend error code (e.g. PRODUCT_NOT_ENTITLED) from the app error envelope. */
export type ApiError = AxiosError & { apiErrorCode?: string };

/** Returns the backend error code of a failed request, if it sent one. */
export function apiErrorCode(error: unknown): string | undefined {
  return (error as ApiError | null)?.apiErrorCode;
}

// Interceptor to attach access token
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor to extract backend's actual error message and handle 401 unauthenticated
apiClient.interceptors.response.use(
  (response) => response,
  (error: ApiError) => {
    // The backend answers in two shapes: FastAPI's {detail} (string or
    // validation array) and the app exception envelope
    // {data: null, meta: {error: {code, message}}} used for e.g.
    // PRODUCT_NOT_ENTITLED. The second one used to be ignored, so the
    // message was lost and the console showed "{}".
    const responseData = error.response?.data as
      | {
          detail?: string | Array<{ msg?: string }>;
          message?: string;
          meta?: { error?: { code?: string; message?: string } } | null;
        }
      | undefined;

    let detailMessage: string | undefined;

    if (responseData) {
      const envelopeError = responseData.meta?.error;
      if (typeof responseData.detail === 'string') {
        detailMessage = responseData.detail;
      } else if (Array.isArray(responseData.detail)) {
        detailMessage = responseData.detail
          // Pydantic prefixes custom validator messages with "Value error, ".
          .map((item) => (typeof item === 'object' && item && item.msg ? item.msg.replace(/^Value error, /, '') : JSON.stringify(item)))
          .join(', ');
      } else if (envelopeError && typeof envelopeError.message === 'string') {
        detailMessage = envelopeError.message;
      } else if (typeof responseData.message === 'string') {
        detailMessage = responseData.message;
      }
      if (envelopeError && typeof envelopeError.code === 'string') {
        error.apiErrorCode = envelopeError.code;
      }
    }

    if (detailMessage) {
      error.message = detailMessage;
    }

    // On 401 Unauthorized: clear tokens, reset auth state, and redirect to login
    if (error.response?.status === 401) {
      clearStoredTokens();
      // Clear Zustand in-memory auth state — .getState() is valid outside React per Zustand docs
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    // A 403 is an expected, handled outcome (the page shows a restricted or
    // "not enabled" state), so it is a warning, not an error. console.error
    // made the Next.js dev overlay report every one as an "Issue".
    if (error.response?.status === 403) {
      console.warn('Permission denied (403):', detailMessage || error.response.data);
    }

    return Promise.reject(error);
  }
);
