import { QueryClient } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { COMMIT_GRACE_MS, refreshAfterWrite } from './refresh-after-write';

afterEach(() => vi.useRealTimers());

describe('refreshAfterWrite: do not re-read in the same millisecond as the write', () => {
  it('waits for the grace period, then invalidates every key', async () => {
    vi.useFakeTimers();
    const client = new QueryClient();
    const spy = vi.spyOn(client, 'invalidateQueries').mockResolvedValue(undefined);
    const done = refreshAfterWrite(client, [['clinics'], ['overview']]);
    await vi.advanceTimersByTimeAsync(COMMIT_GRACE_MS - 1);
    expect(spy).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    await done;
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenCalledWith({ queryKey: ['clinics'] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['overview'] });
  });
  it('graceMs 0 invalidates at once', async () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, 'invalidateQueries').mockResolvedValue(undefined);
    await refreshAfterWrite(client, [['x']], 0);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
