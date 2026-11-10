import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { User } from '../../types/api';

export const USERS_QUERY_KEY = ['users'];

export function useUsers(enabled = true) {
  return useQuery<User[]>({
    queryKey: USERS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get('/users');
      const data = res.data?.data;
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    },
    enabled,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: any) => {
      const res = await apiClient.post('/users', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const res = await apiClient.delete(`/users/${userId}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
    },
  });
}

export function useUserPermissions(userId: string) {
  return useQuery({
    queryKey: [...USERS_QUERY_KEY, userId, 'permissions'],
    queryFn: async () => {
      if (!userId) return [];
      const res = await apiClient.get(`/users/${userId}/permissions`);
      const data = res.data?.data;
      // The editor sends back the full list on save (PUT replaces every override),
      // so an unexpected shape must be an error, never an empty list.
      if (!Array.isArray(data)) {
        throw new Error('Unexpected response while loading permissions');
      }
      return data;
    },
    enabled: !!userId,
  });
}

export function useUpdateUserPermissions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, permissions }: { userId: string; permissions: any[] }) => {
      const res = await apiClient.put(`/users/${userId}/permissions`, permissions);
      return res.data?.data || res.data;
    },
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: [...USERS_QUERY_KEY, userId, 'permissions'] });
    },
  });
}
