/*
 * Types for the AV Platform API (/api/v1/platform/), architecture v2:
 * section 4 (tables), 6.3 (platform auth), 7 (entitlements), 11 (routes).
 *
 * The mock adapter and the HTTP adapter both return exactly these shapes, so
 * screens never change when the adapter does (U6).
 *
 * Patient data never appears here (P-5): no patient name, phone or clinical
 * value in any type. Keep it that way.
 */

/* ------------------------------------------------------------------ */
/* Envelope (backend/app/schemas/envelope.py)                          */
/* ------------------------------------------------------------------ */

export interface MetaPagination {
  total: number;
  page: number;
  page_size: number;
}

export interface MetaErrorDetails {
  code: string;
  message: string;
  field?: string | null;
}

export interface MetaError {
  error: MetaErrorDetails;
}

export interface ResponseEnvelope<T, M = MetaPagination | MetaError | Record<string, unknown>> {
  data: T | null;
  meta: M | null;
}

/** Successful single-object response. */
export type ItemResponse<T> = ResponseEnvelope<T, Record<string, unknown>> & { data: T };

/** Successful paginated list response. */
export type PageResponse<T> = ResponseEnvelope<T[], MetaPagination> & { data: T[]; meta: MetaPagination };

export interface PaginationParams {
  page?: number;
  /** 1 to 100, default 20 (schemas/common.py). */
  page_size?: number;
}

export const PAGE_SIZE_DEFAULT = 20;
export const PAGE_SIZE_MAX = 100;
/** Console list default; one of the DataTable page-size options. */
export const UI_PAGE_SIZE = 25;

/* ------------------------------------------------------------------ */
/* Enums (String + CHECK on the backend, section 0.6)                  */
/* ------------------------------------------------------------------ */

export const ORGANIZATION_TYPES = [
  'individual',
  'clinic',
  'chain',
  'franchise',
  'hospital',
  'government',
  'partner_platform',
] as const;
export type OrganizationType = (typeof ORGANIZATION_TYPES)[number];

export const ACCOUNT_STATUSES = ['active', 'suspended'] as const;
/** organizations.status and clinics.status (4.1). */
export type AccountStatus = (typeof ACCOUNT_STATUSES)[number];

/** enums/clinic.py ClinicType. */
export const CLINIC_TYPES = ['clinic', 'solo', 'personal'] as const;
export type ClinicType = (typeof CLINIC_TYPES)[number];

/** enums/product.py EntitlementStatus. */
export const ENTITLEMENT_STATUSES = ['enabled', 'disabled'] as const;
export type EntitlementStatus = (typeof ENTITLEMENT_STATUSES)[number];

/** enums/product.py EntitlementSource. Console grants are always `direct` (0.9). */
export type EntitlementSource = 'direct' | 'bundle';

/** platform_operators.role (4.2). */
export const OPERATOR_ROLES = ['owner', 'support'] as const;
export type OperatorRole = (typeof OPERATOR_ROLES)[number];

/**
 * Product key as in core/products.py. Kept as a string on purpose: the
 * list of products always comes from the catalog endpoint, never from code.
 */
export type ProductKey = string;

/* ------------------------------------------------------------------ */
/* Auth (6.3)                                                          */
/* ------------------------------------------------------------------ */

export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Step 1 result. No token yet: a token is issued only after MFA.
 * `mfa_enrolment_required` is true on first login (forced enrolment).
 * confirm in S2: exact field names of the challenge response.
 */
export interface LoginChallenge {
  challenge_token: string;
  mfa_enrolment_required: boolean;
  /**
   * Only during enrolment: the otpauth URI to show as a QR code. The mock
   * never returns a value here (no secret is generated or kept).
   * confirm in S2.
   */
  otpauth_uri?: string | null;
}

export interface MfaRequest {
  challenge_token: string;
  /** 6-digit TOTP code. */
  code: string;
}

/** confirm in S2: token response shape. */
export interface PlatformTokenResponse {
  access_token: string;
  token_type: 'bearer';
  /** Seconds. PLATFORM_JWT_EXPIRE_MINUTES = 480. */
  expires_in: number;
  operator: Operator;
}

/* ------------------------------------------------------------------ */
/* Operators (platform_operators, 4.2)                                 */
/* ------------------------------------------------------------------ */

/** Never carries password_hash, mfa_secret or token_version. */
export interface Operator {
  id: string;
  email: string;
  name: string;
  role: OperatorRole;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * decision: S2 (CLI-only today). Operators are created only by
 * `python -m app.scripts.create_platform_operator`; the console never sets a
 * password. Type kept for the route in section 11; the UI does not call it.
 */
export interface OperatorCreate {
  email: string;
  name: string;
  role: OperatorRole;
  reason: string;
}

export interface OperatorUpdate {
  name?: string;
  role?: OperatorRole;
  /** Deactivating increments token_version on the backend (6.3). */
  is_active?: boolean;
  reason: string;
}

/* ------------------------------------------------------------------ */
/* Product catalog                                                     */
/* ------------------------------------------------------------------ */

/**
 * confirm in S3: route not listed in section 11. Mirrors the product list
 * in core/products.py. Products not offered in the console (today:
 * clinical-decision-support) are simply absent from this list.
 */
export interface ProductCatalogItem {
  key: ProductKey;
  name: string;
  description: string;
  category: string;
}

/* ------------------------------------------------------------------ */
/* Organizations (4.1)                                                 */
/* ------------------------------------------------------------------ */

export interface Organization {
  id: string;
  name: string;
  slug: string;
  type: OrganizationType;
  status: AccountStatus;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
  updated_at: string;
}

/** List row. confirm in S3: the counts. */
export interface OrganizationListItem extends Organization {
  clinic_count: number;
  active_clinic_count: number;
}

export interface OrganizationListParams extends PaginationParams {
  search?: string;
  type?: OrganizationType;
  status?: AccountStatus;
}

export interface OrganizationDetail extends Organization {
  clinics: ClinicListItem[];
}

export interface OrganizationCreate {
  name: string;
  slug: string;
  type: OrganizationType;
  contact_email?: string | null;
  contact_phone?: string | null;
  reason: string;
}

export interface OrganizationUpdate {
  name?: string;
  type?: OrganizationType;
  contact_email?: string | null;
  contact_phone?: string | null;
  reason: string;
}

/** Body of suspend / activate for organizations and clinics. */
export interface StatusChangeRequest {
  reason: string;
}

/** Move all clinics of `source_organization_id` into this organization. */
export interface OrganizationMergeRequest {
  source_organization_id: string;
  reason: string;
}

/* ------------------------------------------------------------------ */
/* Clinics                                                             */
/* ------------------------------------------------------------------ */

export interface ClinicListItem {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  type: ClinicType;
  status: AccountStatus;
  staff_count: number;
  last_activity_at: string | null;
  created_at: string;
}

/** POST /organizations/{id}/clinics. confirm in S3: the branch fields. */
export interface ClinicCreate {
  name: string;
  slug: string;
  type: ClinicType;
  reason: string;
}

/** One workspace_products row, as the console sees it. */
export interface Entitlement {
  product_key: ProductKey;
  status: EntitlementStatus;
  source: EntitlementSource;
  valid_from: string | null;
  valid_until: string | null;
  /** True when status is enabled and today is inside the validity window (6.1). */
  is_effective: boolean;
  updated_at: string;
}

/** PUT /clinics/{id}/products/{product_key}. */
export interface EntitlementUpdate {
  status: EntitlementStatus;
  valid_from: string | null;
  valid_until: string | null;
  reason: string;
}

export interface ClinicUsageSummary {
  /** confirm in S3: window of the summary. */
  window_days: number;
  total_events: number;
  by_product: { product_key: ProductKey; events: number }[];
}

export interface ClinicDetail extends ClinicListItem {
  organization_name: string;
  organization_status: AccountStatus;
  products: Entitlement[];
  usage: ClinicUsageSummary;
}

/* ------------------------------------------------------------------ */
/* Usage (usage_events, 4.3)                                           */
/* ------------------------------------------------------------------ */

/** Event types from section 9. confirm in S3. */
export const USAGE_EVENT_TYPES = [
  'login',
  'patient_created',
  'appointment_created',
  'invoice_created',
  'payment_recorded',
  'prescription_created',
  'prescription_pdf',
  'posture_report',
  'posture_pdf',
  'screening_assigned',
  'screening_completed',
] as const;
export type UsageEventType = (typeof USAGE_EVENT_TYPES)[number];

export interface UsageParams extends PaginationParams {
  clinic_id?: string;
  product_key?: ProductKey;
  /** ISO date (YYYY-MM-DD), inclusive. */
  date_from?: string;
  date_to?: string;
}

/** Aggregated row. confirm in S3: grouping (day x clinic x product x event). */
export interface UsageRow {
  date: string;
  clinic_id: string;
  /** `platform` for login / patient_created (section 9). */
  product_key: ProductKey;
  event_type: UsageEventType;
  count: number;
}

/* ------------------------------------------------------------------ */
/* Audit (platform_audit_logs, 4.2)                                    */
/* ------------------------------------------------------------------ */

export type AuditTargetType = 'organization' | 'clinic' | 'entitlement' | 'operator';

export interface AuditLog {
  id: string;
  operator_id: string | null;
  /** confirm in S3: joined for display. */
  operator_name: string | null;
  action: string;
  target_type: AuditTargetType | string;
  target_id: string | null;
  /** confirm in S3: display name of the target, joined (organization, clinic or operator name). */
  target_name: string | null;
  organization_id: string | null;
  clinic_id: string | null;
  reason: string | null;
  ip: string | null;
  user_agent: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogParams extends PaginationParams {
  operator_id?: string;
  organization_id?: string;
  clinic_id?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
}

/* ------------------------------------------------------------------ */
/* Overview                                                            */
/* ------------------------------------------------------------------ */

/** confirm in S3: fields of GET /overview. */
export interface Overview {
  organizations: { total: number; active: number; suspended: number; by_type: Record<OrganizationType, number> };
  clinics: { total: number; active: number; suspended: number };
  products: { product_key: ProductKey; effective_clinics: number }[];
  usage_last_30_days: number;
  recent_audit: AuditLog[];
}
