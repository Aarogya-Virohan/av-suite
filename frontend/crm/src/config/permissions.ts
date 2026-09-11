import { UserRole } from '../types/api';

// ---------------------------------------------------------------------------
// CANONICAL CAPABILITY REGISTRY (64 KEYS)
// Matches backend/app/core/rbac.py (Lead Dev canonical specification)
// Format: module.action (no .manage keys)
// ---------------------------------------------------------------------------

export type CapabilityScope = 'none' | 'own' | 'all';

export type CanonicalCapabilityKey =
  // patients
  | 'patients.view'
  | 'patients.create'
  | 'patients.edit'
  | 'patients.delete'
  // leads
  | 'leads.view'
  | 'leads.create'
  | 'leads.edit'
  | 'leads.delete'
  | 'leads.convert'
  // appointments
  | 'appointments.view'
  | 'appointments.create'
  | 'appointments.edit'
  | 'appointments.delete'
  // treatments
  | 'treatments.view'
  | 'treatments.create'
  | 'treatments.edit'
  | 'treatments.delete'
  // assessments
  | 'assessments.view'
  | 'assessments.create'
  | 'assessments.edit'
  | 'assessments.delete'
  // prescriptions
  | 'prescriptions.view'
  | 'prescriptions.create'
  | 'prescriptions.edit'
  | 'prescriptions.delete'
  // exercises
  | 'exercises.view'
  | 'exercises.create'
  | 'exercises.edit'
  | 'exercises.delete'
  // documents
  | 'documents.view'
  | 'documents.upload'
  | 'documents.edit'
  | 'documents.delete'
  // invoices
  | 'invoices.view'
  | 'invoices.create'
  | 'invoices.edit'
  | 'invoices.delete'
  // payments
  | 'payments.view'
  | 'payments.record'
  | 'payments.delete'
  // packages
  | 'packages.view'
  | 'packages.create'
  | 'packages.edit'
  | 'packages.delete'
  | 'packages.assign'
  // booking
  | 'booking.view'
  | 'booking.approve'
  | 'booking.edit'
  | 'booking.delete'
  // analytics
  | 'analytics.my_performance'
  | 'analytics.clinic_financials'
  // settings
  | 'settings.view'
  | 'settings.edit'
  // users
  | 'users.view'
  | 'users.create'
  | 'users.edit'
  | 'users.delete'
  // permissions
  | 'permissions.view'
  | 'permissions.edit'
  // audit
  | 'audit.view'
  // recycle bin
  | 'recyclebin.view'
  | 'recyclebin.restore'
  // posture
  | 'posture.view'
  | 'posture.create';

export interface CapabilityMeta {
  key: CanonicalCapabilityKey;
  module: string;
  label: string;
  allowedScopes: CapabilityScope[];
}

export const CANONICAL_CAPABILITIES: CapabilityMeta[] = [
  // Patients
  { key: 'patients.view', module: 'Patients', label: 'View Patients', allowedScopes: ['none', 'own', 'all'] },
  { key: 'patients.create', module: 'Patients', label: 'Create Patients', allowedScopes: ['none', 'all'] },
  { key: 'patients.edit', module: 'Patients', label: 'Edit Patients', allowedScopes: ['none', 'own', 'all'] },
  { key: 'patients.delete', module: 'Patients', label: 'Delete Patients', allowedScopes: ['none', 'all'] },
  // Leads
  { key: 'leads.view', module: 'Leads', label: 'View Leads', allowedScopes: ['none', 'own', 'all'] },
  { key: 'leads.create', module: 'Leads', label: 'Create Leads', allowedScopes: ['none', 'all'] },
  { key: 'leads.edit', module: 'Leads', label: 'Edit Leads', allowedScopes: ['none', 'own', 'all'] },
  { key: 'leads.delete', module: 'Leads', label: 'Delete Leads', allowedScopes: ['none', 'all'] },
  { key: 'leads.convert', module: 'Leads', label: 'Convert Leads to Patients', allowedScopes: ['none', 'own', 'all'] },
  // Appointments
  { key: 'appointments.view', module: 'Appointments', label: 'View Appointments', allowedScopes: ['none', 'own', 'all'] },
  { key: 'appointments.create', module: 'Appointments', label: 'Create Appointments', allowedScopes: ['none', 'all'] },
  { key: 'appointments.edit', module: 'Appointments', label: 'Edit / Reschedule Appointments', allowedScopes: ['none', 'own', 'all'] },
  { key: 'appointments.delete', module: 'Appointments', label: 'Cancel / Delete Appointments', allowedScopes: ['none', 'own', 'all'] },
  // Treatments
  { key: 'treatments.view', module: 'Treatments', label: 'View Treatment Sessions', allowedScopes: ['none', 'own', 'all'] },
  { key: 'treatments.create', module: 'Treatments', label: 'Create Treatment Sessions', allowedScopes: ['none', 'all'] },
  { key: 'treatments.edit', module: 'Treatments', label: 'Edit Treatment Sessions', allowedScopes: ['none', 'own', 'all'] },
  { key: 'treatments.delete', module: 'Treatments', label: 'Delete Treatment Sessions', allowedScopes: ['none', 'own', 'all'] },
  // Assessments
  { key: 'assessments.view', module: 'Assessments', label: 'View SOAP Assessments', allowedScopes: ['none', 'own', 'all'] },
  { key: 'assessments.create', module: 'Assessments', label: 'Create SOAP Assessments', allowedScopes: ['none', 'all'] },
  { key: 'assessments.edit', module: 'Assessments', label: 'Edit SOAP Assessments', allowedScopes: ['none', 'own', 'all'] },
  { key: 'assessments.delete', module: 'Assessments', label: 'Delete SOAP Assessments', allowedScopes: ['none', 'own', 'all'] },
  // Prescriptions
  { key: 'prescriptions.view', module: 'Prescriptions', label: 'View Prescriptions', allowedScopes: ['none', 'own', 'all'] },
  { key: 'prescriptions.create', module: 'Prescriptions', label: 'Create Prescriptions', allowedScopes: ['none', 'all'] },
  { key: 'prescriptions.edit', module: 'Prescriptions', label: 'Edit Prescriptions', allowedScopes: ['none', 'own', 'all'] },
  { key: 'prescriptions.delete', module: 'Prescriptions', label: 'Delete Prescriptions', allowedScopes: ['none', 'own', 'all'] },
  // Exercises
  { key: 'exercises.view', module: 'Exercises', label: 'View Exercise Library', allowedScopes: ['none', 'all'] },
  { key: 'exercises.create', module: 'Exercises', label: 'Create Exercises', allowedScopes: ['none', 'all'] },
  { key: 'exercises.edit', module: 'Exercises', label: 'Edit Exercises', allowedScopes: ['none', 'all'] },
  { key: 'exercises.delete', module: 'Exercises', label: 'Delete Exercises', allowedScopes: ['none', 'all'] },
  // Documents
  { key: 'documents.view', module: 'Documents', label: 'View Documents', allowedScopes: ['none', 'own', 'all'] },
  { key: 'documents.upload', module: 'Documents', label: 'Upload Documents', allowedScopes: ['none', 'all'] },
  { key: 'documents.edit', module: 'Documents', label: 'Edit Documents', allowedScopes: ['none', 'own', 'all'] },
  { key: 'documents.delete', module: 'Documents', label: 'Delete Documents', allowedScopes: ['none', 'own', 'all'] },
  // Invoices
  { key: 'invoices.view', module: 'Billing', label: 'View Invoices', allowedScopes: ['none', 'own', 'all'] },
  { key: 'invoices.create', module: 'Billing', label: 'Create Invoices', allowedScopes: ['none', 'all'] },
  { key: 'invoices.edit', module: 'Billing', label: 'Edit Invoices', allowedScopes: ['none', 'all'] },
  { key: 'invoices.delete', module: 'Billing', label: 'Delete Invoices', allowedScopes: ['none', 'all'] },
  // Payments
  { key: 'payments.view', module: 'Billing', label: 'View Payments', allowedScopes: ['none', 'all'] },
  { key: 'payments.record', module: 'Billing', label: 'Record Payments', allowedScopes: ['none', 'all'] },
  { key: 'payments.delete', module: 'Billing', label: 'Delete Payments', allowedScopes: ['none', 'all'] },
  // Packages
  { key: 'packages.view', module: 'Billing', label: 'View Packages', allowedScopes: ['none', 'all'] },
  { key: 'packages.create', module: 'Billing', label: 'Create Packages', allowedScopes: ['none', 'all'] },
  { key: 'packages.edit', module: 'Billing', label: 'Edit Packages', allowedScopes: ['none', 'all'] },
  { key: 'packages.delete', module: 'Billing', label: 'Delete Packages', allowedScopes: ['none', 'all'] },
  { key: 'packages.assign', module: 'Billing', label: 'Assign Packages to Patients', allowedScopes: ['none', 'all'] },
  // Booking
  { key: 'booking.view', module: 'Booking', label: 'View Booking Requests', allowedScopes: ['none', 'all'] },
  { key: 'booking.approve', module: 'Booking', label: 'Approve / Reject Requests', allowedScopes: ['none', 'all'] },
  { key: 'booking.edit', module: 'Booking', label: 'Edit Booking Requests', allowedScopes: ['none', 'all'] },
  { key: 'booking.delete', module: 'Booking', label: 'Delete Booking Requests', allowedScopes: ['none', 'all'] },
  // Analytics
  { key: 'analytics.my_performance', module: 'Analytics', label: 'My Performance Analytics', allowedScopes: ['none', 'own', 'all'] },
  { key: 'analytics.clinic_financials', module: 'Analytics', label: 'Clinic Financial Analytics', allowedScopes: ['none', 'all'] },
  // Settings
  { key: 'settings.view', module: 'Settings', label: 'View Clinic Settings', allowedScopes: ['none', 'all'] },
  { key: 'settings.edit', module: 'Settings', label: 'Edit Clinic Settings', allowedScopes: ['none', 'all'] },
  // Users
  { key: 'users.view', module: 'Staff', label: 'View Staff & Therapists', allowedScopes: ['none', 'all'] },
  { key: 'users.create', module: 'Staff', label: 'Create New Users', allowedScopes: ['none', 'all'] },
  { key: 'users.edit', module: 'Staff', label: 'Edit Users', allowedScopes: ['none', 'all'] },
  { key: 'users.delete', module: 'Staff', label: 'Remove Users', allowedScopes: ['none', 'all'] },
  // Permissions
  { key: 'permissions.view', module: 'Staff', label: 'View User Permissions', allowedScopes: ['none', 'all'] },
  { key: 'permissions.edit', module: 'Staff', label: 'Edit User Permissions', allowedScopes: ['none', 'all'] },
  // Audit
  { key: 'audit.view', module: 'Audit', label: 'View Audit Logs', allowedScopes: ['none', 'all'] },
  // Recycle Bin
  { key: 'recyclebin.view', module: 'Recycle Bin', label: 'View Recycle Bin', allowedScopes: ['none', 'all'] },
  { key: 'recyclebin.restore', module: 'Recycle Bin', label: 'Restore Deleted Items', allowedScopes: ['none', 'all'] },
  // Posture
  { key: 'posture.view', module: 'Posture', label: 'View Posture Analyses', allowedScopes: ['none', 'own', 'all'] },
  { key: 'posture.create', module: 'Posture', label: 'Run Posture Analysis', allowedScopes: ['none', 'all'] },
];

// ---------------------------------------------------------------------------
// CANONICAL ROLE DEFAULT CAPABILITIES
// Matches backend/app/core/rbac.py ROLE_TEMPLATES
// ---------------------------------------------------------------------------
export const CANONICAL_ROLE_TEMPLATES: Record<UserRole, Partial<Record<CanonicalCapabilityKey, CapabilityScope>>> = {
  admin: Object.fromEntries(
    CANONICAL_CAPABILITIES.map((c) => [c.key, c.allowedScopes.includes('all') ? 'all' : 'own'])
  ) as Record<CanonicalCapabilityKey, CapabilityScope>,
  therapist: {
    'patients.view': 'own',
    'patients.create': 'all',
    'patients.edit': 'own',
    'patients.delete': 'none',
    'leads.view': 'none',
    'leads.create': 'none',
    'leads.edit': 'none',
    'leads.delete': 'none',
    'leads.convert': 'none',
    'appointments.view': 'own',
    'appointments.create': 'all',
    'appointments.edit': 'own',
    'appointments.delete': 'own',
    'treatments.view': 'own',
    'treatments.create': 'all',
    'treatments.edit': 'own',
    'treatments.delete': 'own',
    'assessments.view': 'own',
    'assessments.create': 'all',
    'assessments.edit': 'own',
    'assessments.delete': 'none',
    'prescriptions.view': 'own',
    'prescriptions.create': 'all',
    'prescriptions.edit': 'own',
    'prescriptions.delete': 'none',
    'exercises.view': 'all',
    'exercises.create': 'none',
    'exercises.edit': 'none',
    'exercises.delete': 'none',
    'documents.view': 'own',
    'documents.upload': 'all',
    'documents.edit': 'own',
    'documents.delete': 'none',
    'invoices.view': 'none',
    'invoices.create': 'none',
    'invoices.edit': 'none',
    'invoices.delete': 'none',
    'payments.view': 'none',
    'payments.record': 'none',
    'payments.delete': 'none',
    'packages.view': 'none',
    'packages.create': 'none',
    'packages.edit': 'none',
    'packages.delete': 'none',
    'packages.assign': 'none',
    'booking.view': 'none',
    'booking.approve': 'none',
    'booking.edit': 'none',
    'booking.delete': 'none',
    'analytics.my_performance': 'own',
    'analytics.clinic_financials': 'none',
    'settings.view': 'none',
    'settings.edit': 'none',
    'users.view': 'none',
    'users.create': 'none',
    'users.edit': 'none',
    'users.delete': 'none',
    'permissions.view': 'none',
    'permissions.edit': 'none',
    'audit.view': 'none',
    'recyclebin.view': 'none',
    'recyclebin.restore': 'none',
    'posture.view': 'own',
    'posture.create': 'all',
  },
  front_desk: {
    'patients.view': 'all',
    'patients.create': 'all',
    'patients.edit': 'all',
    'patients.delete': 'none',
    'leads.view': 'all',
    'leads.create': 'all',
    'leads.edit': 'all',
    'leads.delete': 'none',
    'leads.convert': 'all',
    'appointments.view': 'all',
    'appointments.create': 'all',
    'appointments.edit': 'all',
    'appointments.delete': 'all',
    'treatments.view': 'none',
    'treatments.create': 'none',
    'treatments.edit': 'none',
    'treatments.delete': 'none',
    'assessments.view': 'none',
    'assessments.create': 'none',
    'assessments.edit': 'none',
    'assessments.delete': 'none',
    'prescriptions.view': 'none',
    'prescriptions.create': 'none',
    'prescriptions.edit': 'none',
    'prescriptions.delete': 'none',
    'exercises.view': 'all',
    'exercises.create': 'none',
    'exercises.edit': 'none',
    'exercises.delete': 'none',
    'documents.view': 'all',
    'documents.upload': 'all',
    'documents.edit': 'all',
    'documents.delete': 'none',
    'invoices.view': 'all',
    'invoices.create': 'all',
    'invoices.edit': 'none',
    'invoices.delete': 'none',
    'payments.view': 'all',
    'payments.record': 'all',
    'payments.delete': 'none',
    'packages.view': 'all',
    'packages.create': 'none',
    'packages.edit': 'none',
    'packages.delete': 'none',
    'packages.assign': 'all',
    'booking.view': 'all',
    'booking.approve': 'all',
    'booking.edit': 'all',
    'booking.delete': 'none',
    'analytics.my_performance': 'none',
    'analytics.clinic_financials': 'none',
    'settings.view': 'none',
    'settings.edit': 'none',
    'users.view': 'all',
    'users.create': 'none',
    'users.edit': 'none',
    'users.delete': 'none',
    'permissions.view': 'none',
    'permissions.edit': 'none',
    'audit.view': 'none',
    'recyclebin.view': 'none',
    'recyclebin.restore': 'none',
    'posture.view': 'none',
    'posture.create': 'none',
  },
  patient: {},
};

export function getCapabilityScope(
  role: UserRole | null,
  key: CanonicalCapabilityKey,
  userOverrides?: Record<string, string> | null
): CapabilityScope {
  if (!role) return 'none';
  if (userOverrides && key in userOverrides) {
    return userOverrides[key] as CapabilityScope;
  }
  return CANONICAL_ROLE_TEMPLATES[role]?.[key] || 'none';
}

export function hasCapability(
  role: UserRole | null,
  key: CanonicalCapabilityKey,
  userOverrides?: Record<string, string> | null
): boolean {
  const scope = getCapabilityScope(role, key, userOverrides);
  return scope === 'own' || scope === 'all';
}

// ---------------------------------------------------------------------------
// BACKEND ALIGNMENT (COARSE MAP)
// Deprecated role map, strictly aligned with backend/app/core/rbac.py
// clinic_admin restricted to ADMIN only per Lead Dev directive
// ---------------------------------------------------------------------------
export const BACKEND_PERMISSION_MAP: Record<string, UserRole[]> = {
  patients: ['admin', 'therapist', 'front_desk'],
  treatments: ['admin', 'therapist'],
  assessments: ['admin', 'therapist'],
  billing: ['admin', 'front_desk'],
  analytics: ['admin', 'therapist'],
  leads: ['admin', 'front_desk'],
  documents: ['admin', 'therapist', 'front_desk'],
  appointments: ['admin', 'therapist', 'front_desk'],
  exercises: ['admin', 'therapist'],
  posture: ['admin', 'therapist'],
  prescriptions: ['admin', 'therapist'],
  settings: ['admin'],
  packages: ['admin'],
  clinic_admin: ['admin'], // Patched: [ADMIN] only (was allowing therapist/front_desk)
  booking: ['admin', 'therapist', 'front_desk'],
  appointment_requests: ['admin', 'therapist', 'front_desk'],
};

export function hasBackendPermission(role: UserRole, resource: string): boolean {
  const allowedRoles = BACKEND_PERMISSION_MAP[resource];
  return allowedRoles ? allowedRoles.includes(role) : false;
}

// ---------------------------------------------------------------------------
// FRONTEND UI MAPPINGS
// ---------------------------------------------------------------------------
export interface ModuleVisibility {
  dashboard: boolean;
  patients: boolean;
  appointments: boolean;
  analytics: boolean;
  billing: boolean;
  leads: boolean;
  therapists: boolean;
  recycleBin: boolean;
  settings: boolean;
}

export interface PatientTabVisibility {
  timeline: boolean;
  documents: boolean;
  treatments: boolean;
  soapNotes: boolean;
  assessments: boolean;
  billing: boolean;
}

export interface ActionPermissions {
  createEditPatient: boolean;
  deletePatient: boolean;
  manageAppointments: boolean;
  createEditSoapNote: boolean;
  createInvoiceRecordPayment: boolean;
  createSellPackage: boolean;
  uploadDownloadDocuments: boolean;
  restoreDeletedRecords: boolean;
  manageUsersAndRoles: boolean;
  updateClinicSettings: boolean;
}

export interface RolePermissions {
  sidebar: ModuleVisibility;
  patientTabs: PatientTabVisibility;
  actions: ActionPermissions;
}

export const PERMISSIONS_MATRIX: Record<UserRole, RolePermissions> = {
  admin: {
    sidebar: {
      dashboard: true,
      patients: true,
      appointments: true,
      analytics: true,
      billing: true,
      leads: true,
      therapists: true,
      recycleBin: true,
      settings: true,
    },
    patientTabs: {
      timeline: true,
      documents: true,
      treatments: true,
      soapNotes: true,
      assessments: true,
      billing: true,
    },
    actions: {
      createEditPatient: true,
      deletePatient: true,
      manageAppointments: true,
      createEditSoapNote: true,
      createInvoiceRecordPayment: true,
      createSellPackage: true,
      uploadDownloadDocuments: true,
      restoreDeletedRecords: true,
      manageUsersAndRoles: true,
      updateClinicSettings: true,
    },
  },
  therapist: {
    sidebar: {
      dashboard: true,
      patients: hasCapability('therapist', 'patients.view'),
      appointments: hasCapability('therapist', 'appointments.view'),
      analytics: hasCapability('therapist', 'analytics.my_performance'),
      billing: false,
      leads: false,
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: true,
      documents: hasCapability('therapist', 'documents.view'),
      treatments: hasCapability('therapist', 'treatments.view'),
      soapNotes: hasCapability('therapist', 'assessments.view'),
      assessments: hasCapability('therapist', 'assessments.view'),
      billing: false,
    },
    actions: {
      createEditPatient: hasCapability('therapist', 'patients.create') || hasCapability('therapist', 'patients.edit'),
      deletePatient: false,
      manageAppointments: hasCapability('therapist', 'appointments.edit'),
      createEditSoapNote: hasCapability('therapist', 'assessments.create') || hasCapability('therapist', 'assessments.edit'),
      createInvoiceRecordPayment: false,
      createSellPackage: false,
      uploadDownloadDocuments: hasCapability('therapist', 'documents.upload'),
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
    },
  },
  front_desk: {
    sidebar: {
      dashboard: true,
      patients: hasCapability('front_desk', 'patients.view'),
      appointments: hasCapability('front_desk', 'appointments.view'),
      analytics: false,
      billing: hasCapability('front_desk', 'invoices.view'),
      leads: hasCapability('front_desk', 'leads.view'),
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: true,
      documents: hasCapability('front_desk', 'documents.view'),
      treatments: false,
      soapNotes: false,
      assessments: false,
      billing: hasCapability('front_desk', 'invoices.view'),
    },
    actions: {
      createEditPatient: hasCapability('front_desk', 'patients.create') || hasCapability('front_desk', 'patients.edit'),
      deletePatient: false,
      manageAppointments: hasCapability('front_desk', 'appointments.edit') || hasCapability('front_desk', 'appointments.create'),
      createEditSoapNote: false,
      createInvoiceRecordPayment: hasCapability('front_desk', 'invoices.create') || hasCapability('front_desk', 'payments.record'),
      createSellPackage: hasCapability('front_desk', 'packages.assign'),
      uploadDownloadDocuments: hasCapability('front_desk', 'documents.upload'),
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
    },
  },
  patient: {
    sidebar: {
      dashboard: false,
      patients: false,
      appointments: false,
      analytics: false,
      billing: false,
      leads: false,
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: false,
      documents: false,
      treatments: false,
      soapNotes: false,
      assessments: false,
      billing: false,
    },
    actions: {
      createEditPatient: false,
      deletePatient: false,
      manageAppointments: false,
      createEditSoapNote: false,
      createInvoiceRecordPayment: false,
      createSellPackage: false,
      uploadDownloadDocuments: false,
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
    },
  },
};

export function getPermissionsForRole(role: UserRole | null): RolePermissions {
  if (!role) return PERMISSIONS_MATRIX.patient; // fail-closed (deny all)
  return PERMISSIONS_MATRIX[role] || PERMISSIONS_MATRIX.patient;
}

export function canAccessModule(role: UserRole | null, module: keyof ModuleVisibility): boolean {
  if (!role) return false;
  return getPermissionsForRole(role).sidebar[module];
}

export function canPerformAction(role: UserRole | null, action: keyof ActionPermissions): boolean {
  if (!role) return false;
  return getPermissionsForRole(role).actions[action];
}
