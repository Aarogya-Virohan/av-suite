import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { User } from '../../types/api';

export const USERS_QUERY_KEY = ['users'];

export function useUsers() {
  return useQuery<User[]>({
    queryKey: USERS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get('/users');
      const data = res.data?.data;
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    },
  });
}
