'use client';

import { useQuery } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';

export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: async () => (await platformApi().getOverview()).data,
  });
}
