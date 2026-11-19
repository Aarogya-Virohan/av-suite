'use client';

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { ClinicCreate, OrganizationListParams } from '@/lib/platform-api/types';

export const organizationKeys = {
  all: ['organizations'] as const,
  list: (params: OrganizationListParams) => ['organizations', 'list', params] as const,
  detail: (id: string) => ['organizations', 'detail', id] as const,
};

export function useOrganizations(params: OrganizationListParams) {
  return useQuery({
    queryKey: organizationKeys.list(params),
    queryFn: () => platformApi().listOrganizations(params),
    placeholderData: keepPreviousData,
  });
}

export function useOrganization(id: string) {
  return useQuery({
    queryKey: organizationKeys.detail(id),
    queryFn: async () => (await platformApi().getOrganization(id)).data,
  });
}

/** Anything that changes an organization also changes the overview, clinics and audit log. */
function useInvalidateAfterChange() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: organizationKeys.all }),
      queryClient.invalidateQueries({ queryKey: ['clinics'] }),
      queryClient.invalidateQueries({ queryKey: ['overview'] }),
      queryClient.invalidateQueries({ queryKey: ['audit-logs'] }),
    ]);
}

export function useSetOrganizationStatus(id: string) {
  const invalidate = useInvalidateAfterChange();
  return useMutation({
    mutationFn: ({ action, reason }: { action: 'suspend' | 'activate'; reason: string }) =>
      action === 'suspend' ? platformApi().suspendOrganization(id, { reason }) : platformApi().activateOrganization(id, { reason }),
    onSuccess: invalidate,
  });
}

export function useCreateClinic(organizationId: string) {
  const invalidate = useInvalidateAfterChange();
  return useMutation({
    mutationFn: async (body: ClinicCreate) => (await platformApi().createClinic(organizationId, body)).data,
    onSuccess: invalidate,
  });
}
