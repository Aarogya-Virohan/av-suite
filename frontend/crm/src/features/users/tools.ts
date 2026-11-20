import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { USERS_QUERY_KEY } from './api';

/**
 * Tool checkboxes per user (CRM-6, BE-1 contract in tracks/crm.md).
 * Keys and order are fixed by the API; labels come from the API when it sends them.
 */
export const TOOL_KEYS = ['psycho-social-screening', 'exercise-library', 'posture-tool'] as const;
export type ToolKey = (typeof TOOL_KEYS)[number];
export type ToolState = Partial<Record<ToolKey, boolean>>;

export const DEFAULT_TOOL_LABELS: Record<ToolKey, string> = {
  'psycho-social-screening': 'Psychosocial',
  'exercise-library': 'Exercise Library',
  'posture-tool': 'Posture',
};

/** One line under each checkbox. Front desk gets Psychosocial as assign only (S-D-036). */
export function toolHint(key: ToolKey, role: string | null | undefined): string {
  if (key === 'psycho-social-screening') {
    return role === 'front_desk'
      ? 'Can send questionnaires to patients. Cannot see the answers.'
      : 'Send questionnaires and see results of own patients.';
  }
  if (key === 'exercise-library') return 'Browse exercises and write prescriptions.';
  return 'Run posture assessments and view reports.';
}

export interface UserTools {
  user_id: string;
  role: string;
  tools: ToolState;
  available: ToolState;
  labels: Partial<Record<ToolKey, string>>;
}

export const toolLabel = (key: ToolKey, labels?: Partial<Record<ToolKey, string>>) => labels?.[key] || DEFAULT_TOOL_LABELS[key];

export const enabledTools = (state: ToolState | undefined): ToolKey[] => TOOL_KEYS.filter((k) => state?.[k]);

export function useUserTools(userId: string | null | undefined, enabled = true) {
  return useQuery<UserTools>({
    queryKey: [...USERS_QUERY_KEY, userId, 'tools'],
    queryFn: async () => {
      const res = await apiClient.get(`/users/${userId}/tools`);
      const data = res.data?.data;
      if (!data || typeof data.tools !== 'object') throw new Error('Unexpected response while loading tool access');
      return data as UserTools;
    },
    enabled: enabled && !!userId,
  });
}

export function useSetUserTools() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, tools }: { userId: string; tools: ToolKey[] }) => {
      const res = await apiClient.put(`/users/${userId}/tools`, { tools });
      return res.data?.data as UserTools;
    },
    onSuccess: (_d, { userId }) => {
      qc.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      qc.invalidateQueries({ queryKey: [...USERS_QUERY_KEY, userId] });
    },
  });
}
