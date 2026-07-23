import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

// Custom request configuration interface to record request timestamp
interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  startTime?: number;
}

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('aarogya_api_url') || DEFAULT_API_URL;
  }
  return DEFAULT_API_URL;
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to start timer
api.interceptors.request.use((config: CustomAxiosRequestConfig) => {
  config.startTime = Date.now();
  
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Update baseURL dynamically in case config changed
    config.baseURL = getApiBaseUrl();
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor with global error handling and execution time benchmark
api.interceptors.response.use((response) => {
  const config = response.config as CustomAxiosRequestConfig;
  if (config.startTime) {
    const latency = Date.now() - config.startTime;
    // Store latency for refresh measurement
    if (typeof window !== 'undefined') {
      localStorage.setItem('api_last_latency', `${latency}ms`);
    }
  }
  return response;
}, (error: AxiosError<any>) => {
  const config = error.config as CustomAxiosRequestConfig;
  if (config && config.startTime) {
    const latency = Date.now() - config.startTime;
    if (typeof window !== 'undefined') {
      localStorage.setItem('api_last_latency', `${latency}ms`);
    }
  }

  if (error.response) {
    const { status, data } = error.response;
    const message = data?.message || data?.detail || 'An unexpected error occurred';

    switch (status) {
      case 401:
        toast.error('Session expired. Please log in again.');
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        break;
      case 403:
        toast.error('Access denied. You do not have permissions for this action.');
        break;
      case 404:
        toast.error('Resource not found.');
        break;
      case 422:
        // Validation errors
        if (data?.detail && Array.isArray(data.detail)) {
          data.detail.forEach((err: any) => {
            toast.error(`Field Error: ${err.loc?.join('.') || ''} - ${err.msg}`);
          });
        } else {
          toast.error(message);
        }
        break;
      case 500:
        toast.error('Internal Server Error. Please retry shortly.');
        break;
      default:
        toast.error(message);
    }
  } else {
    toast.error('Network error. Check your server connection.');
  }

  return Promise.reject(error);
});
