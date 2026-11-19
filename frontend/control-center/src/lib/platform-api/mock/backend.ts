/*
 * In-memory stand-in for the /api/v1/platform/ backend (S2 + S3), so the
 * console can be built and tested before those chunks land.
 *
 * It follows the backend rules the console depends on:
 * - token only after MFA (6.3)
 * - Owner gets every permission, Support only reads (P-7), mutations by
 *   Support give 403 (acceptance 3)
 * - every mutation needs a typed reason and writes one audit row (acceptance 9)
 * - entitlements are effective only inside valid_from / valid_until (acceptance 7)
 * - clinics are never deleted, only suspended (2.6)
 *
 * No real secret, QR data or password is generated or kept for MFA: the
 * mock accepts any 6-digit code and stores nothing about it.
 */
import type { PlatformApi } from '../api';
import { PLATFORM_ERROR_CODES, PlatformApiError } from '../errors';
import { roleHas, type PlatformPermission } from '../../platform-rbac';
import {
  ACCOUNT_STATUSES,
  CLINIC_TYPES,
  ENTITLEMENT_STATUSES,
  OPERATOR_ROLES,
  ORGANIZATION_TYPES,
  PAGE_SIZE_DEFAULT,
  PAGE_SIZE_MAX,
  type AuditLog,
  type AuditTargetType,
  type ClinicDetail,
  type ClinicListItem,
  type Entitlement,
  type ItemResponse,
  type Operator,
  type OrganizationDetail,
  type OrganizationListItem,
  type Organization,
  type PageResponse,
  type PaginationParams,
  type ProductCatalogItem,
  type UsageEventType,
  type UsageRow,
} from '../types';
import {
  buildSeed,
  createRng,
  mockId,
  SEED_CATALOG,
  type SeedClinic,
  type SeedEntitlement,
  type SeedOperator,
  type SeedOrganization,
} from './seed';

const TOKEN_TTL_SECONDS = 480 * 60; // PLATFORM_JWT_EXPIRE_MINUTES
const REASON_MAX = 1000;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DAY = 24 * 60 * 60 * 1000;

/** Which event types each product records (section 9). */
const EVENTS_BY_PRODUCT: Record<string, UsageEventType[]> = {
  platform: ['login', 'patient_created'],
  crm: ['appointment_created', 'invoice_created', 'payment_recorded'],
  'exercise-prescription': ['prescription_created', 'prescription_pdf'],
  'posture-tool': ['posture_report', 'posture_pdf'],
  'psycho-social-screening': ['screening_assigned', 'screening_completed'],
};

function fail(status: number, code: string, message: string, field?: string): never {
  throw new PlatformApiError(status, { code, message, field: field ?? null });
}

function item<T>(data: T): ItemResponse<T> {
  return { data, meta: null } as ItemResponse<T>;
}

function page<T>(rows: T[], params: PaginationParams): PageResponse<T> {
  const pageNo = params.page ?? 1;
  const size = params.page_size ?? PAGE_SIZE_DEFAULT;
  if (!Number.isInteger(pageNo) || pageNo < 1) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'page must be 1 or more.', 'page');
  if (!Number.isInteger(size) || size < 1 || size > PAGE_SIZE_MAX) {
    fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `page_size must be between 1 and ${PAGE_SIZE_MAX}.`, 'page_size');
  }
  const start = (pageNo - 1) * size;
  return { data: rows.slice(start, start + size), meta: { total: rows.length, page: pageNo, page_size: size } };
}

function requireReason(reason: unknown): string {
  const text = typeof reason === 'string' ? reason.trim() : '';
  if (!text) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'A reason is required.', 'reason');
  if (text.length > REASON_MAX) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `Reason is limited to ${REASON_MAX} characters.`, 'reason');
  return text;
}

function requireOneOf<T extends string>(value: unknown, allowed: readonly T[], field: string): T {
  if (typeof value !== 'string' || !allowed.includes(value as T)) {
    fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `${field} must be one of: ${allowed.join(', ')}.`, field);
  }
  return value as T;
}

function requireText(value: unknown, field: string, max: number): string {
  const text = typeof value === 'string' ? value.trim() : '';
  if (!text) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `${field} is required.`, field);
  if (text.length > max) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `${field} is limited to ${max} characters.`, field);
  return text;
}

function parseOptionalDate(value: unknown, field: string): number | null {
  if (value === null || value === undefined || value === '') return null;
  const ms = typeof value === 'string' ? Date.parse(value) : Number.NaN;
  if (Number.isNaN(ms)) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, `${field} is not a valid date.`, field);
  return ms;
}

/** Simple string hash for deterministic usage numbers. */
function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) h = Math.imul(h ^ text.charCodeAt(i), 16777619) >>> 0;
  return h;
}

export interface MockBackendOptions {
  /** Clock, injectable for tests. */
  now?: () => Date;
  /** State saved by exportState(), to survive a page reload. */
  state?: MockBackendState | null;
}

/** Serializable mock state (fictional data only). */
export interface MockBackendState {
  version: 2;
  operators: SeedOperator[];
  usageProfile: Record<string, string[]>;
  organizations: SeedOrganization[];
  clinics: SeedClinic[];
  entitlements: SeedEntitlement[];
  auditLogs: AuditLog[];
  challenges: [string, string][];
  sessions: [string, { operatorId: string; version: number; expiresAt: number }][];
  tokenVersions: [string, number][];
  counter: number;
}

export class MockPlatformBackend {
  private readonly now: () => Date;
  private operators: SeedOperator[];
  private organizations: SeedOrganization[];
  private clinics: SeedClinic[];
  private entitlements: SeedEntitlement[];
  private auditLogs: AuditLog[] = [];
  /**
   * Which products each clinic has history for. Fixed at seed time: usage
   * is history, so suspending a clinic or changing a tool later must not
   * rewrite past counts. New clinics start with none.
   */
  private usageProfile: Record<string, string[]> = {};
  private readonly catalog: ProductCatalogItem[] = SEED_CATALOG;
  /** challenge token -> operator id (between login and MFA). */
  private readonly challenges = new Map<string, string>();
  /** access token -> operator id + version, like the JWT `ver` claim. */
  private readonly sessions = new Map<string, { operatorId: string; version: number; expiresAt: number }>();
  private readonly tokenVersions = new Map<string, number>();
  private counter = 0;

  constructor(options: MockBackendOptions = {}) {
    this.now = options.now ?? (() => new Date());
    const state = options.state;
    if (state && state.version === 2) {
      this.operators = state.operators;
      this.usageProfile = state.usageProfile;
      this.organizations = state.organizations;
      this.clinics = state.clinics;
      this.entitlements = state.entitlements;
      this.auditLogs = state.auditLogs;
      state.challenges.forEach(([k, v]) => this.challenges.set(k, v));
      state.sessions.forEach(([k, v]) => this.sessions.set(k, v));
      state.tokenVersions.forEach(([k, v]) => this.tokenVersions.set(k, v));
      this.counter = state.counter;
      return;
    }
    const seed = buildSeed(this.now());
    this.operators = seed.operators;
    this.organizations = seed.organizations;
    this.clinics = seed.clinics;
    this.entitlements = seed.entitlements;
    this.usageProfile = this.buildUsageProfile();
    this.seedAuditHistory();
  }

  exportState(): MockBackendState {
    return {
      version: 2,
      operators: this.operators,
      usageProfile: this.usageProfile,
      organizations: this.organizations,
      clinics: this.clinics,
      entitlements: this.entitlements,
      auditLogs: this.auditLogs,
      challenges: [...this.challenges.entries()],
      sessions: [...this.sessions.entries()],
      tokenVersions: [...this.tokenVersions.entries()],
      counter: this.counter,
    };
  }

  /** Build the PlatformApi bound to a token provider. */
  api(getToken: () => string | null): PlatformApi {
    const auth = (permission: PlatformPermission) => this.authorize(getToken(), permission);
    return {
      login: async (body) => item(this.login(body.email, body.password)),
      verifyMfa: async (body) => item(this.verifyMfa(body.challenge_token, body.code)),

      getOverview: async () => {
        auth('platform.usage.read');
        return item(this.overview());
      },
      getUsage: async (params) => {
        auth('platform.usage.read');
        return page(this.usageRows(params.clinic_id, params.product_key, params.date_from, params.date_to), params);
      },
      listProducts: async () => {
        auth('platform.organizations.read');
        return item(this.catalog.map((p) => ({ ...p })));
      },

      listOrganizations: async (params) => {
        auth('platform.organizations.read');
        const search = params.search?.trim().toLowerCase();
        if (params.type) requireOneOf(params.type, ORGANIZATION_TYPES, 'type');
        if (params.status) requireOneOf(params.status, ACCOUNT_STATUSES, 'status');
        const rows = this.organizations
          .filter((o) => !search || o.name.toLowerCase().includes(search) || o.slug.includes(search))
          .filter((o) => !params.type || o.type === params.type)
          .filter((o) => !params.status || o.status === params.status)
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((o) => this.toListItem(o));
        return page(rows, params);
      },
      createOrganization: async (body) => {
        const op = auth('platform.organizations.manage');
        const reason = requireReason(body.reason);
        const name = requireText(body.name, 'name', 255);
        const slug = this.requireFreeSlug(body.slug, 'organization');
        const type = requireOneOf(body.type, ORGANIZATION_TYPES, 'type');
        const contactEmail = this.optionalEmail(body.contact_email);
        const ts = this.now().toISOString();
        const org: SeedOrganization = {
          id: this.newId('org'),
          name,
          slug,
          type,
          status: 'active',
          contact_email: contactEmail,
          contact_phone: body.contact_phone?.trim() || null,
          created_at: ts,
          updated_at: ts,
        };
        this.organizations.push(org);
        this.audit(op, 'organization.create', 'organization', org.id, { organization_id: org.id }, reason, {
          before: null,
          after: { name, slug, type, status: 'active', contact_email: org.contact_email, contact_phone: org.contact_phone },
        });
        return item(this.toOrganization(org));
      },
      getOrganization: async (id) => {
        auth('platform.organizations.read');
        return item(this.organizationDetail(this.findOrganization(id)));
      },
      updateOrganization: async (id, body) => {
        const op = auth('platform.organizations.manage');
        const reason = requireReason(body.reason);
        const org = this.findOrganization(id);
        const before = { name: org.name, type: org.type, contact_email: org.contact_email, contact_phone: org.contact_phone };
        if (body.name !== undefined) org.name = requireText(body.name, 'name', 255);
        if (body.type !== undefined) org.type = requireOneOf(body.type, ORGANIZATION_TYPES, 'type');
        if (body.contact_email !== undefined) org.contact_email = this.optionalEmail(body.contact_email);
        if (body.contact_phone !== undefined) org.contact_phone = body.contact_phone?.trim() || null;
        org.updated_at = this.now().toISOString();
        const after = { name: org.name, type: org.type, contact_email: org.contact_email, contact_phone: org.contact_phone };
        this.audit(op, 'organization.update', 'organization', org.id, { organization_id: org.id }, reason, { before, after });
        return item(this.toOrganization(org));
      },
      suspendOrganization: async (id, body) => item(this.setOrganizationStatus(auth('platform.organizations.manage'), id, 'suspended', body.reason)),
      activateOrganization: async (id, body) => item(this.setOrganizationStatus(auth('platform.organizations.manage'), id, 'active', body.reason)),
      createClinic: async (organizationId, body) => {
        const op = auth('platform.organizations.manage');
        const reason = requireReason(body.reason);
        const org = this.findOrganization(organizationId);
        const name = requireText(body.name, 'name', 255);
        const slug = this.requireFreeSlug(body.slug, 'clinic');
        const type = requireOneOf(body.type, CLINIC_TYPES, 'type');
        const clinic: SeedClinic = {
          id: this.newId('clinic'),
          organization_id: org.id,
          name,
          slug,
          type,
          status: 'active',
          staff_count: 0,
          last_activity_at: null,
          created_at: this.now().toISOString(),
        };
        this.clinics.push(clinic);
        this.audit(op, 'clinic.create', 'clinic', clinic.id, { organization_id: org.id, clinic_id: clinic.id }, reason, {
          before: null,
          after: { name, slug, type, status: 'active', organization_id: org.id },
        });
        return item(this.toClinicListItem(clinic));
      },
      mergeOrganization: async (id, body) => {
        const op = auth('platform.organizations.manage');
        const reason = requireReason(body.reason);
        const target = this.findOrganization(id);
        const source = this.findOrganization(body.source_organization_id);
        if (source.id === target.id) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'Cannot merge an organization into itself.', 'source_organization_id');
        const moved = this.clinics.filter((c) => c.organization_id === source.id);
        const movedIds = moved.map((c) => c.id);
        moved.forEach((c) => {
          c.organization_id = target.id;
        });
        this.audit(op, 'organization.merge', 'organization', target.id, { organization_id: target.id }, reason, {
          source_organization_id: source.id,
          moved_clinic_ids: movedIds,
          before: { organization_id: source.id },
          after: { organization_id: target.id },
        });
        return item(this.organizationDetail(target));
      },

      getClinic: async (id) => {
        auth('platform.organizations.read');
        return item(this.clinicDetail(this.findClinic(id)));
      },
      suspendClinic: async (id, body) => item(this.setClinicStatus(auth('platform.organizations.manage'), id, 'suspended', body.reason)),
      activateClinic: async (id, body) => item(this.setClinicStatus(auth('platform.organizations.manage'), id, 'active', body.reason)),

      setClinicProduct: async (clinicId, productKey, body) => {
        const op = auth('platform.entitlements.manage');
        const reason = requireReason(body.reason);
        const clinic = this.findClinic(clinicId);
        if (!this.catalog.some((p) => p.key === productKey)) fail(404, PLATFORM_ERROR_CODES.NOT_FOUND, 'Unknown product.', 'product_key');
        const status = requireOneOf(body.status, ENTITLEMENT_STATUSES, 'status');
        const fromMs = parseOptionalDate(body.valid_from, 'valid_from');
        const untilMs = parseOptionalDate(body.valid_until, 'valid_until');
        if (fromMs !== null && untilMs !== null && untilMs <= fromMs) {
          fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'valid_until must be after valid_from.', 'valid_until');
        }
        let row = this.entitlements.find((e) => e.clinic_id === clinic.id && e.product_key === productKey);
        const before = row ? { status: row.status, valid_from: row.valid_from, valid_until: row.valid_until } : null;
        const ts = this.now().toISOString();
        if (!row) {
          row = { clinic_id: clinic.id, product_key: productKey, status, valid_from: null, valid_until: null, updated_at: ts };
          this.entitlements.push(row);
        }
        row.status = status;
        row.valid_from = fromMs === null ? null : new Date(fromMs).toISOString();
        row.valid_until = untilMs === null ? null : new Date(untilMs).toISOString();
        row.updated_at = ts;
        this.audit(op, 'entitlement.update', 'entitlement', `${clinic.id}:${productKey}`, {
          organization_id: clinic.organization_id,
          clinic_id: clinic.id,
        }, reason, { product_key: productKey, before, after: { status: row.status, valid_from: row.valid_from, valid_until: row.valid_until } });
        return item(this.toEntitlement(row));
      },

      listAuditLogs: async (params) => {
        auth('platform.audit.read');
        const fromMs = parseOptionalDate(params.date_from, 'date_from');
        const toMs = parseOptionalDate(params.date_to, 'date_to');
        const action = params.action?.trim();
        const rows = this.auditLogs
          .filter((a) => !params.operator_id || a.operator_id === params.operator_id)
          .filter((a) => !params.organization_id || a.organization_id === params.organization_id)
          .filter((a) => !params.clinic_id || a.clinic_id === params.clinic_id)
          .filter((a) => !action || a.action === action)
          .filter((a) => fromMs === null || Date.parse(a.created_at) >= fromMs)
          .filter((a) => toMs === null || Date.parse(a.created_at) < toMs + DAY)
          .sort((a, b) => b.created_at.localeCompare(a.created_at));
        return page(rows, params);
      },

      listOperators: async (params) => {
        auth('platform.operators.manage');
        return page(
          [...this.operators].sort((a, b) => a.role.localeCompare(b.role) || a.name.localeCompare(b.name)).map((o) => this.toOperator(o)),
          params,
        );
      },
      createOperator: async (body) => {
        const op = auth('platform.operators.manage');
        const reason = requireReason(body.reason);
        const email = requireText(body.email, 'email', 255).toLowerCase();
        if (!EMAIL_PATTERN.test(email)) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'Enter a valid email.', 'email');
        if (this.operators.some((o) => o.email === email)) fail(409, PLATFORM_ERROR_CODES.CONFLICT, 'An operator with this email exists.', 'email');
        const name = requireText(body.name, 'name', 255);
        const role = requireOneOf(body.role, OPERATOR_ROLES, 'role');
        const ts = this.now().toISOString();
        // decision: S2 (CLI-only today). Kept so the mock matches the route; the UI never calls it.
        const created: SeedOperator = {
          id: this.newId('operator'),
          email,
          name,
          role,
          is_active: true,
          mfa_enabled: false,
          mockNeedsEnrolment: true,
          last_login_at: null,
          created_at: ts,
          updated_at: ts,
        };
        this.operators.push(created);
        this.audit(op, 'operator.create', 'operator', created.id, {}, reason, {
          before: null,
          after: { email, name, role, is_active: true, mfa_enabled: false },
        });
        return item(this.toOperator(created));
      },
      updateOperator: async (id, body) => {
        const op = auth('platform.operators.manage');
        const reason = requireReason(body.reason);
        const target = this.operators.find((o) => o.id === id) ?? fail(404, PLATFORM_ERROR_CODES.NOT_FOUND, 'Operator not found.');
        // P-7: the Owner set (Shivank, Daman, Onkar) changes only through the CLI.
        if (target.role === 'owner' && (body.is_active !== undefined || (body.role !== undefined && body.role !== target.role))) {
          fail(403, PLATFORM_ERROR_CODES.FORBIDDEN, 'Owner changes via CLI only.');
        }
        if (target.id === op.id && (body.is_active === false || (body.role && body.role !== target.role))) {
          fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'You cannot deactivate yourself or change your own role.');
        }
        const before = { name: target.name, role: target.role, is_active: target.is_active };
        const next: SeedOperator = {
          ...target,
          name: body.name !== undefined ? requireText(body.name, 'name', 255) : target.name,
          role: body.role !== undefined ? requireOneOf(body.role, OPERATOR_ROLES, 'role') : target.role,
          is_active: body.is_active ?? target.is_active,
          updated_at: this.now().toISOString(),
        };
        if (before.is_active && !next.is_active) {
          // Deactivation invalidates every token of the operator (6.3).
          this.tokenVersions.set(target.id, (this.tokenVersions.get(target.id) ?? 0) + 1);
        }
        this.operators = this.operators.map((o) => (o.id === id ? next : o));
        this.audit(op, 'operator.update', 'operator', target.id, {}, reason, {
          before,
          after: { name: next.name, role: next.role, is_active: next.is_active },
        });
        return item(this.toOperator(next));
      },
    };
  }

  /* ---------------- auth ---------------- */

  private login(email: string, password: string) {
    const normalized = (email ?? '').trim().toLowerCase();
    const operator = this.operators.find((o) => o.email === normalized);
    // Same answer for unknown email, wrong password and inactive operator.
    if (!operator || !operator.is_active || typeof password !== 'string' || password.length < 8) {
      fail(401, PLATFORM_ERROR_CODES.UNAUTHORIZED, 'Email or password is incorrect.');
    }
    const challenge = this.newToken('challenge');
    this.challenges.set(challenge, operator.id);
    return { challenge_token: challenge, mfa_enrolment_required: operator.mockNeedsEnrolment, otpauth_uri: null };
  }

  private verifyMfa(challengeToken: string, code: string) {
    const operatorId = this.challenges.get(challengeToken);
    if (!operatorId) fail(401, PLATFORM_ERROR_CODES.UNAUTHORIZED, 'Sign-in expired. Start again.');
    if (!/^\d{6}$/.test(code ?? '')) fail(401, PLATFORM_ERROR_CODES.MFA_INVALID, 'The code is not valid.', 'code');
    this.challenges.delete(challengeToken);
    const ts = this.now().toISOString();
    this.operators = this.operators.map((o) =>
      o.id === operatorId ? { ...o, mfa_enabled: true, mockNeedsEnrolment: false, last_login_at: ts } : o,
    );
    const token = this.newToken('access');
    this.sessions.set(token, {
      operatorId,
      version: this.tokenVersions.get(operatorId) ?? 0,
      expiresAt: this.now().getTime() + TOKEN_TTL_SECONDS * 1000,
    });
    const operator = this.operators.find((o) => o.id === operatorId)!;
    return { access_token: token, token_type: 'bearer' as const, expires_in: TOKEN_TTL_SECONDS, operator: this.toOperator(operator) };
  }

  private authorize(token: string | null, permission: PlatformPermission): SeedOperator {
    const session = token ? this.sessions.get(token) : undefined;
    if (!session || session.expiresAt <= this.now().getTime()) fail(401, PLATFORM_ERROR_CODES.UNAUTHORIZED, 'Please sign in again.');
    const operator = this.operators.find((o) => o.id === session.operatorId);
    if (!operator || !operator.is_active || (this.tokenVersions.get(operator.id) ?? 0) !== session.version) {
      fail(401, PLATFORM_ERROR_CODES.UNAUTHORIZED, 'Please sign in again.');
    }
    if (!roleHas(operator.role, permission)) fail(403, PLATFORM_ERROR_CODES.FORBIDDEN, 'Your role cannot do this.');
    return operator;
  }

  /* ---------------- reads ---------------- */

  private findOrganization(id: string): SeedOrganization {
    return this.organizations.find((o) => o.id === id) ?? fail(404, PLATFORM_ERROR_CODES.NOT_FOUND, 'Organization not found.');
  }

  private findClinic(id: string): SeedClinic {
    return this.clinics.find((c) => c.id === id) ?? fail(404, PLATFORM_ERROR_CODES.NOT_FOUND, 'Clinic not found.');
  }

  private isEffective(e: SeedEntitlement): boolean {
    const now = this.now().getTime();
    if (e.status !== 'enabled') return false;
    if (e.valid_from && Date.parse(e.valid_from) > now) return false;
    if (e.valid_until && Date.parse(e.valid_until) <= now) return false;
    return true;
  }

  private toOrganization(o: SeedOrganization): Organization {
    return { ...o };
  }

  private toListItem(o: SeedOrganization): OrganizationListItem {
    const own = this.clinics.filter((c) => c.organization_id === o.id);
    return { ...o, clinic_count: own.length, active_clinic_count: own.filter((c) => c.status === 'active').length };
  }

  private toClinicListItem(c: SeedClinic): ClinicListItem {
    return { ...c };
  }

  private toEntitlement(e: SeedEntitlement): Entitlement {
    return {
      product_key: e.product_key,
      status: e.status,
      source: 'direct',
      valid_from: e.valid_from,
      valid_until: e.valid_until,
      is_effective: this.isEffective(e),
      updated_at: e.updated_at,
    };
  }

  private toOperator(o: SeedOperator): Operator {
    const { mockNeedsEnrolment: _hidden, ...rest } = o;
    void _hidden;
    return { ...rest };
  }

  private organizationDetail(o: SeedOrganization): OrganizationDetail {
    return {
      ...this.toOrganization(o),
      clinics: this.clinics.filter((c) => c.organization_id === o.id).map((c) => this.toClinicListItem(c)),
    };
  }

  private clinicDetail(c: SeedClinic): ClinicDetail {
    const org = this.findOrganization(c.organization_id);
    const rows = this.usageRows(c.id, undefined, undefined, undefined);
    const byProduct = new Map<string, number>();
    rows.forEach((r) => byProduct.set(r.product_key, (byProduct.get(r.product_key) ?? 0) + r.count));
    return {
      ...this.toClinicListItem(c),
      organization_name: org.name,
      organization_status: org.status,
      products: this.entitlements.filter((e) => e.clinic_id === c.id).map((e) => this.toEntitlement(e)),
      usage: {
        window_days: 30,
        total_events: rows.reduce((sum, r) => sum + r.count, 0),
        by_product: [...byProduct.entries()].map(([product_key, events]) => ({ product_key, events })),
      },
    };
  }

  /**
   * Daily usage rows, deterministic per clinic, product, event and day.
   * Only active clinics with an effective entitlement record product events.
   */
  private buildUsageProfile(): Record<string, string[]> {
    const profile: Record<string, string[]> = {};
    this.clinics.forEach((c) => {
      profile[c.id] = this.entitlements.filter((e) => e.clinic_id === c.id && this.isEffective(e)).map((e) => e.product_key);
    });
    return profile;
  }

  private usageRows(clinicId?: string, productKey?: string, dateFrom?: string, dateTo?: string): UsageRow[] {
    const today = new Date(this.now().toISOString().slice(0, 10)).getTime();
    const fromMs = parseOptionalDate(dateFrom, 'date_from') ?? today - 29 * DAY;
    const toMs = parseOptionalDate(dateTo, 'date_to') ?? today;
    if (toMs < fromMs) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'date_to must be on or after date_from.', 'date_to');
    if (toMs - fromMs > 366 * DAY) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'Date range is limited to one year.', 'date_to');
    // Every clinic, whatever its status today: suspension blocks new events, it does not erase old ones.
    const clinics = this.clinics.filter((c) => !clinicId || c.id === clinicId);
    const rows: UsageRow[] = [];
    for (let day = toMs; day >= fromMs; day -= DAY) {
      const date = new Date(day).toISOString().slice(0, 10);
      for (const clinic of clinics) {
        if (date < clinic.created_at.slice(0, 10)) continue;
        const history = this.usageProfile[clinic.id];
        if (!history) continue; // created in the console after seeding: no events yet
        const products = ['platform', ...history];
        for (const product of products) {
          if (productKey && product !== productKey) continue;
          for (const eventType of EVENTS_BY_PRODUCT[product] ?? []) {
            const count = hash(`${clinic.id}|${eventType}|${date}`) % (clinic.staff_count + 3);
            if (count > 0) rows.push({ date, clinic_id: clinic.id, product_key: product, event_type: eventType, count });
          }
        }
      }
    }
    return rows;
  }

  private overview() {
    const byType = Object.fromEntries(ORGANIZATION_TYPES.map((t) => [t, 0])) as Record<(typeof ORGANIZATION_TYPES)[number], number>;
    this.organizations.forEach((o) => {
      byType[o.type] += 1;
    });
    const activeOrgIds = new Set(this.organizations.filter((o) => o.status === 'active').map((o) => o.id));
    const liveClinicIds = new Set(this.clinics.filter((c) => c.status === 'active' && activeOrgIds.has(c.organization_id)).map((c) => c.id));
    return {
      organizations: {
        total: this.organizations.length,
        active: activeOrgIds.size,
        suspended: this.organizations.length - activeOrgIds.size,
        by_type: byType,
      },
      clinics: {
        total: this.clinics.length,
        active: this.clinics.filter((c) => c.status === 'active').length,
        suspended: this.clinics.filter((c) => c.status === 'suspended').length,
      },
      products: this.catalog.map((p) => ({
        product_key: p.key,
        effective_clinics: this.entitlements.filter((e) => e.product_key === p.key && liveClinicIds.has(e.clinic_id) && this.isEffective(e)).length,
      })),
      usage_last_30_days: this.usageRows().reduce((sum, r) => sum + r.count, 0),
      recent_audit: [...this.auditLogs].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 8),
    };
  }

  /* ---------------- writes ---------------- */

  private setOrganizationStatus(op: SeedOperator, id: string, status: 'active' | 'suspended', rawReason: unknown): Organization {
    const reason = requireReason(rawReason);
    const org = this.findOrganization(id);
    if (org.status === status) fail(409, PLATFORM_ERROR_CODES.CONFLICT, `Organization is already ${status}.`);
    const before = { status: org.status };
    org.status = status;
    org.updated_at = this.now().toISOString();
    this.audit(op, status === 'suspended' ? 'organization.suspend' : 'organization.activate', 'organization', org.id, { organization_id: org.id }, reason, {
      before,
      after: { status },
    });
    return this.toOrganization(org);
  }

  private setClinicStatus(op: SeedOperator, id: string, status: 'active' | 'suspended', rawReason: unknown): ClinicListItem {
    const reason = requireReason(rawReason);
    const clinic = this.findClinic(id);
    if (clinic.status === status) fail(409, PLATFORM_ERROR_CODES.CONFLICT, `Clinic is already ${status}.`);
    const before = { status: clinic.status };
    clinic.status = status;
    this.audit(op, status === 'suspended' ? 'clinic.suspend' : 'clinic.activate', 'clinic', clinic.id, {
      organization_id: clinic.organization_id,
      clinic_id: clinic.id,
    }, reason, { before, after: { status } });
    return this.toClinicListItem(clinic);
  }

  private requireFreeSlug(value: unknown, kind: 'organization' | 'clinic'): string {
    const slug = requireText(value, 'slug', 120).toLowerCase();
    if (!SLUG_PATTERN.test(slug)) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'Use lowercase letters, numbers and single hyphens.', 'slug');
    const taken = kind === 'organization' ? this.organizations.some((o) => o.slug === slug) : this.clinics.some((c) => c.slug === slug);
    if (taken) fail(409, PLATFORM_ERROR_CODES.CONFLICT, 'This slug is already used.', 'slug');
    return slug;
  }

  private optionalEmail(value: string | null | undefined): string | null {
    const email = value?.trim().toLowerCase() || null;
    if (email && !EMAIL_PATTERN.test(email)) fail(422, PLATFORM_ERROR_CODES.VALIDATION_ERROR, 'Enter a valid email.', 'contact_email');
    return email;
  }

  private audit(
    op: SeedOperator | null,
    action: string,
    targetType: AuditTargetType,
    targetId: string,
    scope: { organization_id?: string; clinic_id?: string },
    reason: string | null,
    details: Record<string, unknown> = {},
    at?: string,
  ) {
    this.auditLogs.push({
      id: this.newId('audit'),
      operator_id: op?.id ?? null,
      operator_name: op?.name ?? null,
      action,
      target_type: targetType,
      target_id: targetId,
      target_name: this.targetName(targetType, targetId, scope.clinic_id),
      organization_id: scope.organization_id ?? null,
      clinic_id: scope.clinic_id ?? null,
      reason,
      ip: null,
      user_agent: null,
      details,
      created_at: at ?? this.now().toISOString(),
    });
  }

  /** Name of the audit target at the time of the change. */
  private targetName(targetType: AuditTargetType, targetId: string, clinicId?: string): string | null {
    if (targetType === 'organization') return this.organizations.find((o) => o.id === targetId)?.name ?? null;
    if (targetType === 'clinic' || targetType === 'entitlement') {
      const id = targetType === 'clinic' ? targetId : clinicId;
      return this.clinics.find((c) => c.id === id)?.name ?? null;
    }
    if (targetType === 'operator') return this.operators.find((o) => o.id === targetId)?.name ?? null;
    return null;
  }

  /** A short, believable history so the audit screen is not empty on first open. */
  private seedAuditHistory() {
    const rnd = createRng(7);
    const owners = this.operators.filter((o) => o.role === 'owner');
    const nowMs = this.now().getTime();
    this.organizations
      .filter((o) => o.status === 'suspended')
      .forEach((o, i) => {
        this.audit(owners[i % owners.length], 'organization.suspend', 'organization', o.id, { organization_id: o.id }, 'Payment overdue, contract on hold', { before: { status: 'active' }, after: { status: 'suspended' } }, new Date(nowMs - (3 + i) * DAY).toISOString());
      });
    this.clinics
      .filter((c) => c.status === 'suspended')
      .forEach((c, i) => {
        this.audit(owners[(i + 1) % owners.length], 'clinic.suspend', 'clinic', c.id, { organization_id: c.organization_id, clinic_id: c.id }, 'Branch closed for renovation', { before: { status: 'active' }, after: { status: 'suspended' } }, new Date(nowMs - (2 + i) * DAY).toISOString());
      });
    this.entitlements.slice(0, 12).forEach((e, i) => {
      const clinic = this.clinics.find((c) => c.id === e.clinic_id)!;
      this.audit(owners[i % owners.length], 'entitlement.update', 'entitlement', `${e.clinic_id}:${e.product_key}`, {
        organization_id: clinic.organization_id,
        clinic_id: clinic.id,
      }, 'Onboarding: tools as per signed order form', {
        product_key: e.product_key,
        before: null,
        after: { status: e.status, valid_from: e.valid_from, valid_until: e.valid_until },
      }, new Date(nowMs - Math.floor(5 + rnd() * 20) * DAY).toISOString());
    });
  }

  private newId(kind: string): string {
    this.counter += 1;
    return mockId(`${kind}:${this.counter}:${this.now().getTime()}`);
  }

  private newToken(kind: string): string {
    this.counter += 1;
    const random = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Math.random()}`.slice(2);
    return `mock-${kind}.${random}.${this.counter}`;
  }
}
