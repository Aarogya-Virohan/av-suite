'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { EntitlementUpdate } from '@/lib/platform-api/types';

export const clinicKeys = {
  all: ['clinics'] as const,
  detail: (id: string) => ['clinics', 'detail', id] as const,
};

export function useClinic(id: string) {
  return useQuery({
    queryKey: clinicKeys.detail(id),
    queryFn: async () => (await platformApi().getClinic(id)).data,
  });
}

function useInvalidateAfterChange() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: clinicKeys.all }),
      queryClient.invalidateQueries({ queryKey: ['organizations'] }),
      queryClient.invalidateQueries({ queryKey: ['overview'] }),
      queryClient.invalidateQueries({ queryKey: ['audit-logs'] }),
    ]);
}

export function useSetClinicStatus(id: string) {
  const invalidate = useInvalidateAfterChange();
  return useMutation({
    mutationFn: ({ action, reason }: { action: 'suspend' | 'activate'; reason: string }) =>
      action === 'suspend' ? platformApi().suspendClinic(id, { reason }) : platformApi().activateClinic(id, { reason }),
    onSuccess: invalidate,
  });
}

export function useSetEntitlement(clinicId: string) {
  const invalidate = useInvalidateAfterChange();
  return useMutation({
    mutationFn: async ({ productKey, body }: { productKey: string; body: EntitlementUpdate }) =>
      (await platformApi().setClinicProduct(clinicId, productKey, body)).data,
    onSuccess: invalidate,
  });
}
