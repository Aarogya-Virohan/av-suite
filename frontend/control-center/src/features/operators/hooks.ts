'use client';

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { OperatorUpdate, PaginationParams } from '@/lib/platform-api/types';

export const operatorKeys = {
  all: ['operators'] as const,
  list: (params: PaginationParams) => ['operators', 'list', params] as const,
};

/** Owner only (platform.operators.manage). Pass enabled=false for anyone else. */
export function useOperators(params: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: operatorKeys.list(params),
    queryFn: () => platformApi().listOperators(params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useUpdateOperator() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: OperatorUpdate }) => (await platformApi().updateOperator(id, body)).data,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: operatorKeys.all }),
        queryClient.invalidateQueries({ queryKey: ['audit-logs'] }),
        queryClient.invalidateQueries({ queryKey: ['overview'] }),
      ]),
  });
}
