import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';

/** Clinic fee list (CRM-2, backend PR #71: /settings/fee-items). */
export type FeeCategory = 'consultation' | 'posture' | 'exercise_rx' | 'custom';

export const FEE_CATEGORIES: { value: FeeCategory; label: string }[] = [
  { value: 'consultation', label: 'Consultation' },
  { value: 'posture', label: 'Posture assessment' },
  { value: 'exercise_rx', label: 'Exercise prescription' },
  { value: 'custom', label: 'Treatment / Other' },
];

export const feeCategoryLabel = (c: string) => FEE_CATEGORIES.find((x) => x.value === c)?.label ?? c;

export interface FeeItem {
  id: string;
  clinic_id: string;
  name: string;
  category: FeeCategory;
  /** Decimal string from the API, e.g. "800.00". */
  default_price: string;
  price_editable: boolean;
  active: boolean;
  sort_order: number;
}

export interface FeeItemInput {
  name: string;
  category: FeeCategory;
  default_price: string;
  price_editable: boolean;
  sort_order?: number;
}

export const FEE_ITEMS_KEY = ['fee-items'];

/** GET needs invoices.create; only active items come back, in sort order. */
export function useFeeItems(enabled = true) {
  return useQuery<FeeItem[]>({
    queryKey: FEE_ITEMS_KEY,
    queryFn: async () => {
      const res = await apiClient.get('/settings/fee-items');
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled,
  });
}

export function useSaveFeeItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, values }: { id?: string; values: FeeItemInput }) => {
      const res = id
        ? await apiClient.patch(`/settings/fee-items/${id}`, values)
        : await apiClient.post('/settings/fee-items', values);
      return res.data as FeeItem;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: FEE_ITEMS_KEY }),
  });
}

/** Soft delete: the server sets active = false, old invoices keep their lines. */
export function useRemoveFeeItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/settings/fee-items/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: FEE_ITEMS_KEY }),
  });
}

/** "800", "800.5", "800.50" -> "800.50"; null when not a valid non-negative price. */
export function normalizePrice(raw: string): string | null {
  const t = raw.trim();
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(t)) return null;
  return Number(t).toFixed(2);
}
