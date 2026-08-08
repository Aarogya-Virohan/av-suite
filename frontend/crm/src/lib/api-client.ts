import axios, { AxiosError } from 'axios';
import { getStoredToken, clearStoredTokens } from './auth';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
export const API_BASE_URL = `${BASE_URL}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  (error: AxiosError) => {
    // Surface backend's actual error detail (FastAPI detail string or array)
    const responseData = error.response?.data as
      | { detail?: string | Array<{ msg?: string }>; message?: string }
      | undefined;

    let detailMessage: string | undefined;

    if (responseData) {
      if (typeof responseData.detail === 'string') {
        detailMessage = responseData.detail;
      } else if (Array.isArray(responseData.detail)) {
        detailMessage = responseData.detail
          .map((item) => (typeof item === 'object' && item && item.msg ? item.msg : JSON.stringify(item)))
          .join(', ');
      } else if (typeof responseData.message === 'string') {
        detailMessage = responseData.message;
      }
    }

    if (detailMessage) {
      error.message = detailMessage;
    }

    // On 401 Unauthorized: clear tokens and redirect to login
    if (error.response?.status === 401) {
      clearStoredTokens();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    if (error.response?.status === 403) {
      console.error('Permission denied (403):', detailMessage || error.response.data);
    }

    return Promise.reject(error);
  }
);
