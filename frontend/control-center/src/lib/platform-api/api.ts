import type {
  AuditLog,
  AuditLogParams,
  ClinicCreate,
  ClinicDetail,
  ClinicListItem,
  Entitlement,
  EntitlementUpdate,
  ItemResponse,
  LoginChallenge,
  LoginRequest,
  MfaRequest,
  Operator,
  OperatorCreate,
  OperatorUpdate,
  Organization,
  OrganizationCreate,
  OrganizationDetail,
  OrganizationListItem,
  OrganizationListParams,
  OrganizationMergeRequest,
  OrganizationUpdate,
  Overview,
  PageResponse,
  PaginationParams,
  PlatformTokenResponse,
  ProductCatalogItem,
  StatusChangeRequest,
  UsageParams,
  UsageRow,
} from './types';

/**
 * One method per route of section 11 (all under /api/v1/platform/).
 * Every adapter (mock, http) implements this interface. Failures throw
 * PlatformApiError; successes return the backend envelope unchanged.
 */
export interface PlatformApi {
  // auth (public)
  login(body: LoginRequest): Promise<ItemResponse<LoginChallenge>>;
  verifyMfa(body: MfaRequest): Promise<ItemResponse<PlatformTokenResponse>>;

  // platform.usage.read
  getOverview(): Promise<ItemResponse<Overview>>;
  getUsage(params: UsageParams): Promise<PageResponse<UsageRow>>;

  // any operator. confirm in S3 (not in section 11)
  listProducts(): Promise<ItemResponse<ProductCatalogItem[]>>;

  // platform.organizations.read / manage
  listOrganizations(params: OrganizationListParams): Promise<PageResponse<OrganizationListItem>>;
  createOrganization(body: OrganizationCreate): Promise<ItemResponse<Organization>>;
  getOrganization(id: string): Promise<ItemResponse<OrganizationDetail>>;
  updateOrganization(id: string, body: OrganizationUpdate): Promise<ItemResponse<Organization>>;
  suspendOrganization(id: string, body: StatusChangeRequest): Promise<ItemResponse<Organization>>;
  activateOrganization(id: string, body: StatusChangeRequest): Promise<ItemResponse<Organization>>;
  createClinic(organizationId: string, body: ClinicCreate): Promise<ItemResponse<ClinicListItem>>;
  mergeOrganization(id: string, body: OrganizationMergeRequest): Promise<ItemResponse<OrganizationDetail>>;

  getClinic(id: string): Promise<ItemResponse<ClinicDetail>>;
  suspendClinic(id: string, body: StatusChangeRequest): Promise<ItemResponse<ClinicListItem>>;
  activateClinic(id: string, body: StatusChangeRequest): Promise<ItemResponse<ClinicListItem>>;

  // platform.entitlements.manage
  setClinicProduct(clinicId: string, productKey: string, body: EntitlementUpdate): Promise<ItemResponse<Entitlement>>;

  // platform.audit.read
  listAuditLogs(params: AuditLogParams): Promise<PageResponse<AuditLog>>;

  // platform.operators.manage
  listOperators(params: PaginationParams): Promise<PageResponse<Operator>>;
  /** decision: S2 (CLI-only today). Not used by the UI. */
  createOperator(body: OperatorCreate): Promise<ItemResponse<Operator>>;
  /**
   * Console may only take access away: deactivate any operator (not yourself,
   * not the last active Owner) and reactivate Support. Role changes and Owner
   * reactivation are CLI only (403).
   */
  updateOperator(id: string, body: OperatorUpdate): Promise<ItemResponse<Operator>>;
}

/** Supplies the current platform access token to an adapter. */
export type TokenProvider = () => string | null;
