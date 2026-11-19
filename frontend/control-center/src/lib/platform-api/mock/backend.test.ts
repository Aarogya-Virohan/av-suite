import { describe, expect, it, beforeEach } from 'vitest';
import { MockPlatformBackend } from './backend';
import type { PlatformApi } from '../api';
import { PlatformApiError } from '../errors';

const NOW = new Date('2026-11-19T10:00:00.000Z');

async function signIn(backend: MockPlatformBackend, email: string) {
  let token: string | null = null;
  const api = backend.api(() => token);
  const challenge = await api.login({ email, password: 'correct-horse' });
  const session = await api.verifyMfa({ challenge_token: challenge.data.challenge_token, code: '123456' });
  token = session.data.access_token;
  return { api, operator: session.data.operator };
}

async function expectError(promise: Promise<unknown>, status: number, code: string) {
  const error = await promise.then(() => null, (e: unknown) => e);
  expect(error).toBeInstanceOf(PlatformApiError);
  expect((error as PlatformApiError).status).toBe(status);
  expect((error as PlatformApiError).code).toBe(code);
}

describe('mock platform backend', () => {
  let backend: MockPlatformBackend;
  let owner: PlatformApi;
  let support: PlatformApi;

  beforeEach(async () => {
    backend = new MockPlatformBackend({ now: () => NOW });
    owner = (await signIn(backend, 'onkar@av-console.mock')).api;
    support = (await signIn(backend, 'support@av-console.mock')).api;
  });

  it('gives no token without MFA and rejects a bad code', async () => {
    const api = backend.api(() => null);
    const challenge = await api.login({ email: 'daman@av-console.mock', password: 'correct-horse' });
    expect(challenge.data).not.toHaveProperty('access_token');
    await expectError(api.verifyMfa({ challenge_token: challenge.data.challenge_token, code: '12ab' }), 401, 'MFA_INVALID');
    await expectError(api.getOverview(), 401, 'UNAUTHORIZED');
  });

  it('flags first-login enrolment and never returns an MFA secret', async () => {
    const api = backend.api(() => null);
    const challenge = await api.login({ email: 'new.support@av-console.mock', password: 'correct-horse' });
    expect(challenge.data.mfa_enrolment_required).toBe(true);
    expect(challenge.data.otpauth_uri ?? null).toBeNull();
  });

  it('paginates with the backend envelope and caps page_size', async () => {
    const res = await owner.listOrganizations({ page: 1, page_size: 5 });
    expect(res.data).toHaveLength(5);
    expect(res.meta).toEqual({ total: expect.any(Number), page: 1, page_size: 5 });
    await expectError(owner.listOrganizations({ page_size: 101 }), 422, 'VALIDATION_ERROR');
  });

  it('serves the catalog without clinical-decision-support', async () => {
    const res = await owner.listProducts();
    expect(res.data.map((p) => p.key)).toEqual(['crm', 'exercise-library', 'exercise-prescription', 'posture-tool', 'psycho-social-screening']);
  });

  it('blocks every mutation for Support with 403 (acceptance 3)', async () => {
    const org = (await support.listOrganizations({ page_size: 1 })).data[0];
    await expectError(support.suspendOrganization(org.id, { reason: 'test' }), 403, 'FORBIDDEN');
    await expectError(support.listOperators({}), 403, 'FORBIDDEN');
  });

  it('requires a reason and writes exactly one audit row per mutation (acceptance 9)', async () => {
    const org = (await owner.listOrganizations({ status: 'active', page_size: 1 })).data[0];
    await expectError(owner.suspendOrganization(org.id, { reason: '   ' }), 422, 'VALIDATION_ERROR');
    const before = (await owner.listAuditLogs({ page_size: 100 })).meta.total;
    await owner.suspendOrganization(org.id, { reason: 'Contract paused' });
    const after = await owner.listAuditLogs({ page_size: 1 });
    expect(after.meta.total).toBe(before + 1);
    expect(after.data[0]).toMatchObject({ action: 'organization.suspend', organization_id: org.id, reason: 'Contract paused' });
  });

  it('treats entitlements outside their window as not effective (acceptance 7)', async () => {
    const org = (await owner.listOrganizations({ page_size: 1 })).data[0];
    const clinic = (await owner.getOrganization(org.id)).data.clinics[0];
    const past = await owner.setClinicProduct(clinic.id, 'posture-tool', {
      status: 'enabled', valid_from: '2026-01-01T00:00:00Z', valid_until: '2026-11-01T00:00:00Z', reason: 'trial ended',
    });
    expect(past.data.is_effective).toBe(false);
    const future = await owner.setClinicProduct(clinic.id, 'posture-tool', {
      status: 'enabled', valid_from: '2026-12-01T00:00:00Z', valid_until: null, reason: 'starts next month',
    });
    expect(future.data.is_effective).toBe(false);
    await expectError(
      owner.setClinicProduct(clinic.id, 'posture-tool', { status: 'enabled', valid_from: '2026-12-01T00:00:00Z', valid_until: '2026-11-30T00:00:00Z', reason: 'x' }),
      422,
      'VALIDATION_ERROR',
    );
    await expectError(owner.setClinicProduct(clinic.id, 'clinical-decision-support', { status: 'enabled', valid_from: null, valid_until: null, reason: 'x' }), 404, 'NOT_FOUND');
  });

  it('invalidates a deactivated operator token (acceptance 4)', async () => {
    const { operator } = await signIn(backend, 'support@av-console.mock');
    await owner.updateOperator(operator.id, { is_active: false, reason: 'left the company' });
    await expectError(support.getOverview(), 401, 'UNAUTHORIZED');
  });

  it('protects Owners: role change and deactivation are CLI only (P-7)', async () => {
    const owners = (await owner.listOperators({})).data.filter((o) => o.role === 'owner');
    const daman = owners.find((o) => o.email === 'daman@av-console.mock')!;
    await expectError(owner.updateOperator(daman.id, { is_active: false, reason: 'x' }), 403, 'FORBIDDEN');
    await expectError(owner.updateOperator(daman.id, { role: 'support', reason: 'x' }), 403, 'FORBIDDEN');
    const audits = (await owner.listAuditLogs({ action: 'operator.update' })).meta.total;
    expect(audits).toBe(0);
  });

  it('writes before and after on every mutation audit row', async () => {
    const org = (await owner.listOrganizations({ status: 'active', page_size: 2 })).data;
    const detail = (await owner.getOrganization(org[0].id)).data;
    const supportOp = (await owner.listOperators({})).data.find((o) => o.role === 'support' && o.is_active)!;
    const created = (await owner.createOrganization({ name: 'Audit Test Org', slug: 'audit-test-org', type: 'clinic', reason: 'r' })).data;
    await owner.updateOrganization(created.id, { name: 'Audit Test Org 2', reason: 'r' });
    await owner.suspendOrganization(created.id, { reason: 'r' });
    await owner.activateOrganization(created.id, { reason: 'r' });
    const branch = (await owner.createClinic(created.id, { name: 'Audit Branch', slug: 'audit-branch', type: 'clinic', reason: 'r' })).data;
    await owner.suspendClinic(branch.id, { reason: 'r' });
    await owner.activateClinic(branch.id, { reason: 'r' });
    await owner.setClinicProduct(branch.id, 'crm', { status: 'enabled', valid_from: null, valid_until: null, reason: 'r' });
    await owner.mergeOrganization(created.id, { source_organization_id: org[1].id, reason: 'r' });
    await owner.updateOperator(supportOp.id, { name: 'Renamed Support', reason: 'r' });
    void detail;
    const rows = (await owner.listAuditLogs({ page_size: 10 })).data;
    expect(rows.map((r) => r.action).sort()).toEqual(
      [
        'organization.create', 'organization.update', 'organization.suspend', 'organization.activate', 'clinic.create',
        'clinic.suspend', 'clinic.activate', 'entitlement.update', 'organization.merge', 'operator.update',
      ].sort(),
    );
    for (const row of rows) {
      expect(row.details, row.action).toHaveProperty('before');
      expect(row.details, row.action).toHaveProperty('after');
      expect(row.details.after, row.action).not.toBeNull();
      expect(row.target_name, row.action).toBeTruthy();
    }
    const opRow = rows.find((r) => r.action === 'operator.update')!;
    expect(opRow.details).toMatchObject({ before: { name: supportOp.name }, after: { name: 'Renamed Support' } });
  });

  it('keeps usage history when a clinic or organization is suspended or a tool changes', async () => {
    const org = (await owner.listOrganizations({ type: 'chain', status: 'active', page_size: 1 })).data[0];
    const clinic = (await owner.getOrganization(org.id)).data.clinics[0];
    const before = (await owner.getClinic(clinic.id)).data.usage.total_events;
    const overviewBefore = (await owner.getOverview()).data.usage_last_30_days;
    expect(before).toBeGreaterThan(0);
    await owner.suspendClinic(clinic.id, { reason: 'r' });
    await owner.suspendOrganization(org.id, { reason: 'r' });
    await owner.setClinicProduct(clinic.id, 'crm', { status: 'disabled', valid_from: null, valid_until: null, reason: 'r' });
    expect((await owner.getClinic(clinic.id)).data.usage.total_events).toBe(before);
    expect((await owner.getOverview()).data.usage_last_30_days).toBe(overviewBefore);
  });

  it('treats an end date as inclusive through the end of that IST day', async () => {
    const org = (await owner.listOrganizations({ page_size: 1 })).data[0];
    const clinic = (await owner.getOrganization(org.id)).data.clinics[0];
    // NOW = 19 Nov 15:30 IST; end date 19 Nov -> stored bound 20 Nov 00:00 IST.
    const res = await owner.setClinicProduct(clinic.id, 'posture-tool', {
      status: 'enabled', valid_from: null, valid_until: '2026-11-19T18:30:00.000Z', reason: 'last day today',
    });
    expect(res.data.is_effective).toBe(true);
  });

  it('never exposes patient fields', async () => {
    const org = (await owner.listOrganizations({ page_size: 1 })).data[0];
    const clinic = (await owner.getClinic((await owner.getOrganization(org.id)).data.clinics[0].id)).data;
    const text = JSON.stringify([clinic, await owner.getOverview(), await owner.getUsage({ page_size: 100 })]).toLowerCase();
    expect(text).not.toMatch(/patient_name|"phone"|diagnosis|first_name/);
  });
});

describe('mock state persistence', () => {
  it('restores data and sessions from exportState', async () => {
    const first = new MockPlatformBackend({ now: () => NOW });
    const { api } = await signIn(first, 'onkar@av-console.mock');
    const org = (await api.listOrganizations({ status: 'active', page_size: 1 })).data[0];
    await api.suspendOrganization(org.id, { reason: 'persist check' });
    const second = new MockPlatformBackend({ now: () => NOW, state: JSON.parse(JSON.stringify(first.exportState())) });
    const token = [...(first.exportState().sessions)][0][0];
    const again = second.api(() => token);
    expect((await again.getOrganization(org.id)).data.status).toBe('suspended');
  });
});
