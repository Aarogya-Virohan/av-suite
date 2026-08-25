import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { AuditLog } from '../../types/api';

export const AUDIT_LOGS_QUERY_KEY = ['audit-logs'];

export function useAuditLogs(page = 1, page_size = 50) {
  return useQuery({
    queryKey: [...AUDIT_LOGS_QUERY_KEY, { page, page_size }],
    queryFn: async () => {
      const res = await apiClient.get('/audit', {
        params: { page, page_size },
      });
      return res.data as { data: AuditLog[]; meta: any };
    },
  });
}
