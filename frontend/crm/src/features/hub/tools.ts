import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { toolUrl, type ToolKey } from '../../lib/hub';

/**
 * HUB-3: the clinical tools in the CRM launcher. A tool is usable when the
 * clinic has the product enabled (entitlement) AND the user has the tool's
 * capability. /auth/me capabilities are role/override scopes only, they do
 * not include the entitlement, so both are needed.
 */
export interface ToolDef {
  key: Exclude<ToolKey, 'crm'>;
  label: string;
  product: string;
  /** Any of these with scope own/all lets the user open the tool. */
  capabilities: string[];
}

export const TOOLS: ToolDef[] = [
  { key: 'exercises', label: 'Exercise Library', product: 'exercise-library', capabilities: ['exercises.view'] },
  { key: 'posture', label: 'Posture Analysis', product: 'posture-tool', capabilities: ['posture.view'] },
  {
    key: 'screening',
    label: 'Psychosocial Screening',
    product: 'psycho-social-screening',
    capabilities: ['screening.assign', 'screening.view'],
  },
];

export type ToolState =
  | { kind: 'open'; href: string }
  | { kind: 'not-in-plan' }
  | { kind: 'no-access' }
  | { kind: 'unavailable' };

interface InstalledProduct {
  product_key: string;
  status: string;
}

/** Enabled product keys of the active clinic, or null while unknown. */
export function useEnabledProducts(enabled: boolean) {
  return useQuery({
    queryKey: ['hub', 'enabled-products'],
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
    queryFn: async (): Promise<Set<string>> => {
      const res = await apiClient.get('/marketplace/installed');
      const rows = (res.data?.data ?? res.data ?? []) as InstalledProduct[];
      return new Set(rows.filter((r) => r.status === 'enabled').map((r) => r.product_key));
    },
  });
}

export function toolState(
  tool: ToolDef,
  enabledProducts: Set<string> | null | undefined,
  capabilities: Record<string, string>,
): ToolState {
  const href = toolUrl(tool.key);
  if (!href) return { kind: 'unavailable' };
  // Unknown entitlement (request failed): do not block; the tool itself
  // still checks the entitlement on every API call.
  if (enabledProducts && !enabledProducts.has(tool.product)) return { kind: 'not-in-plan' };
  const allowed = tool.capabilities.some((c) => {
    const scope = capabilities[c];
    return scope === 'own' || scope === 'all';
  });
  if (!allowed) return { kind: 'no-access' };
  return { kind: 'open', href };
}

export const TOOL_STATE_TEXT: Record<Exclude<ToolState['kind'], 'open'>, string> = {
  'not-in-plan': 'Not in your plan',
  'no-access': 'Ask your admin for access',
  unavailable: 'Not available yet',
};
