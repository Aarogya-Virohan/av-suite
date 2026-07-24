import { api } from '@/lib/axios';
import { setAuthToken, removeAuthToken } from '@/lib/cookieAuth';

export interface LoginPayload {
  email: string;
  password?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
    name: string;
    role: string;
    clinic_id: string;
  };
}

export const authApi = {
  login: async (credentials: LoginPayload): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', credentials);
    const data: AuthResponse = response.data.data || response.data;
    if (data && data.access_token) {
      setAuthToken(data.access_token);
    }
    return data;
  },

  logout: async (): Promise<void> => {
    removeAuthToken();
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  },

  refresh: async (): Promise<{ access_token: string }> => {
    const response = await api.post('/auth/refresh');
    const data = response.data.data || response.data;
    if (data && data.access_token) {
      setAuthToken(data.access_token);
    }
    return data;
  },

  me: async (): Promise<NonNullable<AuthResponse['user']>> => {
    const response = await api.get('/auth/me');
    return response.data.data || response.data;
  }
};

export default authApi;
