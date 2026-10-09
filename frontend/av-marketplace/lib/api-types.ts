export type UserRole = 'admin' | 'therapist' | 'front_desk' | 'patient';
export type WorkspaceType = 'clinic' | 'solo' | 'personal';
export type EntitlementStatus = 'enabled' | 'disabled';
export type EntitlementSource = 'direct' | 'bundle';

export interface ApiEnvelope<T> {
  data: T;
  meta?: unknown;
}

export interface PlatformUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

export interface Workspace {
  id: string;
  name: string;
  type: WorkspaceType;
  role: UserRole;
}

export interface ActiveProduct {
  key: string;
  name: string;
  description: string | null;
  status: EntitlementStatus;
  source: EntitlementSource;
  valid_from: string | null;
  valid_until: string | null;
}

export interface MarketplaceEntitlement {
  product_key: string;
  status: EntitlementStatus;
  source: EntitlementSource;
  valid_from: string | null;
  valid_until: string | null;
}

export interface PlatformContext {
  user: PlatformUser;
  workspaces: Workspace[];
  active_workspace: Workspace | null;
  active_products: ActiveProduct[];
  capabilities: string[];
}

export interface MarketplaceProduct {
  product_key: string;
  name: string;
  description: string | null;
  allowed_workspace_types: WorkspaceType[];
  workspace_eligible: boolean;
  installed: boolean;
  enabled: boolean;
}

export interface InstalledProduct {
  product_key: string;
  name: string;
  status: EntitlementStatus;
  source: EntitlementSource;
  valid_from: string | null;
  valid_until: string | null;
}