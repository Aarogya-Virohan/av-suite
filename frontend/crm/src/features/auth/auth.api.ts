import { api } from '@/lib/axios';
import { LoginCredentials, LoginResponse } from './auth.types';

interface LoginEnvelope {
  data?: LoginResponse;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await api.post<LoginEnvelope | LoginResponse>('/auth/login', credentials, {
      skipAuthRedirect: true,
    });
    const payload = 'access_token' in response.data ? response.data : response.data.data;

    if (!payload?.access_token) {
      throw new Error('Login succeeded, but the server did not return an access token.');
    }

    return payload;
  },
};

export default authApi;
