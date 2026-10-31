import { describe, expect, it } from 'vitest';
import { invoicePdfFilename } from './api';

describe('invoicePdfFilename (L-41)', () => {
  it('matches the server file name', () => {
    expect(invoicePdfFilename('invoice', 'INV-0042')).toBe('Invoice-INV-0042.pdf');
    expect(invoicePdfFilename('receipt', 'INV-0042')).toBe('Receipt-INV-0042.pdf');
  });
  it('replaces characters that are unsafe in a file name', () => {
    expect(invoicePdfFilename('receipt', 'INV/2026 01')).toBe('Receipt-INV-2026-01.pdf');
    expect(invoicePdfFilename('invoice', '///')).toBe('Invoice-invoice.pdf');
  });
});
