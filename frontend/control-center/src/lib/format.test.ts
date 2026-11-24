import { describe, expect, it } from 'vitest';
import { auditActionLabel, auditProductKey } from './format';

describe('audit rows as the backend writes them', () => {
  it('labels the real action codes', () => {
    expect(auditActionLabel('clinic.suspended')).toBe('Clinic suspended');
    expect(auditActionLabel('clinic.active')).toBe('Clinic activated');
    expect(auditActionLabel('organization.active')).toBe('Organization activated');
    expect(auditActionLabel('entitlement.updated')).toBe('Tool access changed');
    expect(auditActionLabel('operator.deactivated')).toBe('Operator deactivated');
    expect(auditActionLabel('something.else')).toBe('something.else');
  });
  it('finds the product inside details.before / details.after', () => {
    expect(auditProductKey({ before: null, after: { product_key: 'crm', status: 'enabled' } })).toBe('crm');
    expect(auditProductKey({ before: { product_key: 'posture' }, after: {} })).toBe('posture');
    expect(auditProductKey({ before: { status: 'active' }, after: { status: 'suspended' } })).toBeNull();
  });
});
