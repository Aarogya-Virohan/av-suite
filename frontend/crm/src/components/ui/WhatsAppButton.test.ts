import { afterEach, describe, expect, it, vi } from 'vitest';
import { openWhatsApp } from './WhatsAppButton';

function opened(): string {
  const spy = vi.mocked(window.open);
  return decodeURIComponent(String(spy.mock.calls[0][0]).split('?text=')[1]);
}

describe('openWhatsApp text', () => {
  afterEach(() => vi.restoreAllMocks());

  it('adds the Patient ID to the default greeting', () => {
    vi.spyOn(window, 'open').mockImplementation(() => null);
    openWhatsApp('98765 43210', 'Jane Doe', undefined, 'Grove Physio', 'ADP-000003');
    expect(opened()).toBe('Hi Jane Doe, greetings from Grove Physio.\nPatient ID: ADP-000003');
  });

  it('leaves the line out when there is no Patient ID', () => {
    vi.spyOn(window, 'open').mockImplementation(() => null);
    openWhatsApp('98765 43210', 'Jane Doe', undefined, 'Grove Physio');
    expect(opened()).toBe('Hi Jane Doe, greetings from Grove Physio.');
  });

  it('keeps a message the caller wrote', () => {
    vi.spyOn(window, 'open').mockImplementation(() => null);
    openWhatsApp('98765 43210', 'Jane Doe', 'Invoice INV-1', 'Grove Physio', 'ADP-000003');
    expect(opened()).toBe('Invoice INV-1');
  });
});
