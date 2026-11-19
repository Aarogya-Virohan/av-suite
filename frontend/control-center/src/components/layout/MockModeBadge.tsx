import { API_MODE } from '@/lib/platform-api';
import { Badge } from '@/components/ui/brand';

/** Visible marker whenever the console runs on mock data, so nobody mistakes it for production. */
export function MockModeBadge() {
  if (API_MODE !== 'mock') return null;
  return <Badge tone="warn">Mock data</Badge>;
}
