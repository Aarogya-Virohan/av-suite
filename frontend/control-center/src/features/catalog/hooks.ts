'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { ProductCatalogItem } from '@/lib/platform-api/types';

export const catalogKeys = { all: ['catalog'] as const };

/** Product list from the catalog endpoint. Screens never hardcode product keys. */
export function useProductCatalog() {
  const query = useQuery({
    queryKey: catalogKeys.all,
    queryFn: async () => (await platformApi().listProducts()).data,
    staleTime: 10 * 60_000,
  });
  const byKey = useMemo(() => new Map<string, ProductCatalogItem>((query.data ?? []).map((p) => [p.key, p])), [query.data]);
  return { ...query, products: query.data ?? [], byKey };
}

/** Display name for a product key; `platform` events are core actions. */
export function productLabel(byKey: Map<string, ProductCatalogItem>, key: string): string {
  if (key === 'platform') return 'Platform core';
  return byKey.get(key)?.name ?? key;
}
