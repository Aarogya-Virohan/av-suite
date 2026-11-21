import { describe, expect, it } from 'vitest';
import { cancelBlockReason } from './api';

describe('cancelBlockReason (CRM-4)', () => {
  it('allows unpaid, issued and draft invoices', () => {
    expect(cancelBlockReason({ status: 'unpaid', paid_amount: '0.00' })).toBeNull();
    expect(cancelBlockReason({ status: 'draft', paid_amount: 0 })).toBeNull();
  });
  it('blocks invoices with live payments and cancelled ones', () => {
    expect(cancelBlockReason({ status: 'paid', paid_amount: '800.00' })).toMatch(/void/i);
    expect(cancelBlockReason({ status: 'partial', paid_amount: '100' })).toMatch(/void/i);
    expect(cancelBlockReason({ status: 'cancelled', paid_amount: 0 })).toMatch(/already/i);
  });
});
