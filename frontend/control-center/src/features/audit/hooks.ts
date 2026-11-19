'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { AuditLogParams } from '@/lib/platform-api/types';

export function useAuditLogs(params: AuditLogParams) {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => platformApi().listAuditLogs(params),
    placeholderData: keepPreviousData,
  });
}
