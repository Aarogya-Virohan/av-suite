import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { AuditLog } from '../../types/api';

export const AUDIT_LOGS_QUERY_KEY = ['audit-logs'];

export function useAuditLogs(page = 1, page_size = 50, user_id?: string | null) {
  return useQuery({
    queryKey: [...AUDIT_LOGS_QUERY_KEY, { page, page_size, user_id }],
    queryFn: async () => {
      const params: any = { offset: (page - 1) * page_size, limit: page_size };
      if (user_id) params.user_id = user_id;
      
      const res = await apiClient.get('/audit', {
        params,
      });
      return res.data as { data: AuditLog[]; meta: any };
    },
  });
}
