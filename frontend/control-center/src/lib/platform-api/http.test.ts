import { createServer, type IncomingMessage, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { createHttpPlatformApi } from './http';
import { PlatformApiError } from './errors';

interface Seen {
  method: string;
  url: string;
  auth: string | undefined;
  body: string;
}

let server: Server;
let baseUrl: string;
let seen: Seen[] = [];
let reply: (req: IncomingMessage) => { status: number; body: unknown; raw?: string };

beforeAll(async () => {
  server = createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      seen.push({ method: req.method ?? '', url: req.url ?? '', auth: req.headers.authorization, body: Buffer.concat(chunks).toString() });
      const r = reply(req);
      res.statusCode = r.status;
      res.setHeader('Content-Type', r.raw ? 'text/html' : 'application/json');
      res.end(r.raw ?? JSON.stringify(r.body));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));
beforeEach(() => {
  seen = [];
  reply = () => ({ status: 200, body: { data: [], meta: {} } });
});

const make = (token: string | null = 'tok', onUnauthorized = vi.fn()) => ({ api: createHttpPlatformApi(baseUrl, () => token, onUnauthorized), onUnauthorized });

describe('http adapter: routes', () => {
  it('sends the platform token and calls the real paths', async () => {
    const { api } = make();
    await api.getOverview();
    await api.listProducts();
    await api.listOrganizations({ search: 'abc', page: 2, page_size: 25 });
    await api.getOrganization('o 1');
    await api.getClinic('c1');
    await api.listAuditLogs({ action: 'clinic.suspended', date_from: '2026-11-01' });
    await api.listOperators({ page: 1, page_size: 100 });
    await api.getUsage({ clinic_id: 'c1', page: 1 });
    expect(seen.map((s) => `${s.method} ${s.url}`)).toEqual([
      'GET /api/v1/platform/overview',
      'GET /api/v1/platform/products',
      'GET /api/v1/platform/organizations?search=abc&page=2&page_size=25',
      'GET /api/v1/platform/organizations/o%201',
      'GET /api/v1/platform/clinics/c1',
      'GET /api/v1/platform/audit-logs?action=clinic.suspended&date_from=2026-11-01',
      'GET /api/v1/platform/operators?page=1&page_size=100',
      'GET /api/v1/platform/usage?clinic_id=c1&page=1',
    ]);
    expect(seen.every((s) => s.auth === 'Bearer tok')).toBe(true);
  });

  it('maps every write to its route and body', async () => {
    const { api } = make();
    reply = () => ({ status: 200, body: { data: {}, meta: {} } });
    await api.createOrganization({ name: 'A', slug: 'a', type: 'chain', reason: 'r' });
    await api.updateOrganization('o1', { name: 'B', reason: 'r' });
    await api.suspendOrganization('o1', { reason: 'r' });
    await api.activateOrganization('o1', { reason: 'r' });
    await api.createClinic('o1', { name: 'N', slug: 'n', type: 'clinic', reason: 'r' });
    await api.mergeOrganization('o1', { source_organization_id: 'o2', reason: 'r' });
    await api.suspendClinic('c1', { reason: 'r' });
    await api.activateClinic('c1', { reason: 'r' });
    await api.setClinicProduct('c1', 'crm', { status: 'enabled', valid_from: null, valid_until: null, reason: 'r' });
    await api.updateOperator('p1', { is_active: false, reason: 'r' });
    expect(seen.map((s) => `${s.method} ${s.url}`)).toEqual([
      'POST /api/v1/platform/organizations',
      'PATCH /api/v1/platform/organizations/o1',
      'POST /api/v1/platform/organizations/o1/suspend',
      'POST /api/v1/platform/organizations/o1/activate',
      'POST /api/v1/platform/organizations/o1/clinics',
      'POST /api/v1/platform/organizations/o1/merge',
      'POST /api/v1/platform/clinics/c1/suspend',
      'POST /api/v1/platform/clinics/c1/activate',
      'PUT /api/v1/platform/clinics/c1/products/crm',
      'PATCH /api/v1/platform/operators/p1',
    ]);
    expect(JSON.parse(seen[8].body)).toEqual({ status: 'enabled', valid_from: null, valid_until: null, reason: 'r' });
  });

  it('login and MFA go to the public auth routes without a token', async () => {
    const { api } = make(null);
    reply = () => ({ status: 200, body: { data: { challenge_token: 'c', mfa_enrolment_required: false, otpauth_uri: null }, meta: {} } });
    const res = await api.login({ email: 'a@b.in', password: 'x' });
    await api.verifyMfa({ challenge_token: 'c', code: '123456' });
    expect(res.data.challenge_token).toBe('c');
    expect(seen.map((s) => `${s.method} ${s.url}`)).toEqual(['POST /api/v1/platform/auth/login', 'POST /api/v1/platform/auth/mfa']);
    expect(seen[0].auth).toBeUndefined();
  });

  it('has no POST /operators: createOperator fails locally without a request', async () => {
    const { api } = make();
    await expect(api.createOperator({ email: 'a@b.in', name: 'A', role: 'support', reason: 'r' })).rejects.toMatchObject({ status: 403 });
    expect(seen).toHaveLength(0);
  });
});

describe('http adapter: errors', () => {
  it('401 on a data call signs the operator out; 401 on login does not', async () => {
    const { api, onUnauthorized } = make();
    reply = () => ({ status: 401, body: { data: null, meta: { error: { code: 'UNAUTHORIZED', message: 'Unauthorized', details: {} } } } });
    await expect(api.getOverview()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    await expect(api.login({ email: 'a@b.in', password: 'x' })).rejects.toMatchObject({ status: 401 });
    await expect(api.verifyMfa({ challenge_token: 'c', code: '000000' })).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('maps 403, 409 and 422 from the backend', async () => {
    const { api } = make();
    const env = (code: string, message: string) => ({ data: null, meta: { error: { code, message, details: {} } } });
    reply = () => ({ status: 409, body: env('CONFLICT', 'Cannot deactivate the last active Owner') });
    await expect(api.updateOperator('p1', { is_active: false, reason: 'r' })).rejects.toMatchObject({ status: 409, message: 'Cannot deactivate the last active Owner.' });
    reply = () => ({ status: 422, body: env('VALIDATION_ERROR', 'Operators cannot deactivate themselves') });
    await expect(api.updateOperator('p1', { is_active: false, reason: 'r' })).rejects.toMatchObject({ status: 422, message: 'You cannot deactivate yourself.' });
    reply = () => ({ status: 403, body: env('FORBIDDEN', 'Role changes via CLI only') });
    await expect(api.updateOperator('p1', { role: 'owner', reason: 'r' })).rejects.toMatchObject({ status: 403, field: 'role' });
    reply = () => ({ status: 422, body: { detail: [{ loc: ['body', 'slug'], msg: 'Field required', type: 'missing' }] } });
    await expect(api.createOrganization({ name: 'A', slug: '', type: 'chain', reason: 'r' })).rejects.toMatchObject({ status: 422, field: 'slug' });
  });

  it('an HTML 200 (wrong URL or proxy page) is a failure, not data', async () => {
    const { api } = make();
    reply = () => ({ status: 200, body: null, raw: '<html>login</html>' });
    await expect(api.getOverview()).rejects.toBeInstanceOf(PlatformApiError);
  });

  it('a build with no API URL fails with a clear message and sends nothing', async () => {
    const api = createHttpPlatformApi(null, () => 'tok', vi.fn());
    await expect(api.getOverview()).rejects.toMatchObject({ code: 'CONFIG_ERROR' });
    expect(seen).toHaveLength(0);
  });

  it('an unreachable server is a NETWORK_ERROR', async () => {
    const api = createHttpPlatformApi('http://127.0.0.1:1', () => 'tok', vi.fn());
    await expect(api.getOverview()).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' });
  });
});
