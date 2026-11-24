import type { QueryClient, QueryKey } from '@tanstack/react-query';

/**
 * The backend commits a write after it has already sent its answer
 * (get_db commits after the response). A list or detail request sent in the
 * same millisecond can still read the old row. So after a successful write the
 * console waits a moment before it asks again; the screen then never shows the
 * old state next to a "saved" message. Does not change any request payload.
 */
export const COMMIT_GRACE_MS = 400;

export async function refreshAfterWrite(queryClient: QueryClient, keys: QueryKey[], graceMs: number = COMMIT_GRACE_MS): Promise<void> {
  if (graceMs > 0) await new Promise((resolve) => setTimeout(resolve, graceMs));
  await Promise.all(keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
}
