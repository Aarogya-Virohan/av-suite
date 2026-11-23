'use client';

import { keepPreviousData, useQueries, useQuery } from '@tanstack/react-query';
import { clinicKeys } from '@/features/clinics/hooks';
import { platformApi } from '@/lib/platform-api';
import type { UsageParams } from '@/lib/platform-api/types';

export function useUsage(params: UsageParams) {
  return useQuery({
    queryKey: ['usage', params],
    queryFn: () => platformApi().getUsage(params),
    placeholderData: keepPreviousData,
  });
}

/** Clinic names for the ids on the current page (shares the clinic detail cache). */
export function useClinicNames(ids: string[]) {
  const unique = Array.from(new Set(ids));
  const results = useQueries({
    queries: unique.map((id) => ({
      queryKey: clinicKeys.detail(id),
      queryFn: async () => (await platformApi().getClinic(id)).data,
      staleTime: 5 * 60_000,
    })),
  });
  const names = new Map<string, string>();
  unique.forEach((id, i) => {
    const data = results[i]?.data;
    if (data) names.set(id, data.name);
  });
  return names;
}
